"""Pyprland manager - the core daemon class."""

import asyncio
import contextlib
import importlib
import inspect
import json
import os
import signal
import sys
import tomllib
from collections.abc import Callable
from functools import partial
from typing import Any, cast

from . import constants as pyprland_constants
from .adapters.backend import EnvironmentBackend
from .adapters.hyprland import HyprlandBackend
from .adapters.niri import NiriBackend
from .adapters.proxy import BackendProxy
from .adapters.wayland import WaylandBackend
from .adapters.xorg import XorgBackend
from .ansi import HandlerStyles, colorize
from .common import (
    SharedState,
    get_logger,
    merge,
)
from .config import Configuration
from .constants import (
    CONFIG_FILE,
    CONTROL,
    DEMO_NOTIFICATION_DURATION_MS,
    ERROR_NOTIFICATION_DURATION_MS,
    OLD_CONFIG_FILE,
    PYPR_DEMO,
    TASK_TIMEOUT,
)
from .ipc import set_notify_method
from .models import PyprError, ResponsePrefix
from .plugins.interface import Plugin
from .plugins.pyprland.schema import PYPRLAND_CONFIG_SCHEMA

__all__: list[str] = ["Pyprland"]


def remove_duplicate(names: list[str]) -> Callable:
    """Decorator that removes duplicated calls to handlers in `names`.

    Will check arguments as well.

    Args:
        names: List of handler names to check for duplicates
    """

    def _remove_duplicates(func: Callable) -> Callable:
        """Wrapper for the decorator."""

        async def _wrapper(self: "Pyprland", full_name: str, *args, **kwargs) -> tuple[bool, str]:
            """Wrapper for the function."""
            if full_name in names:
                key = (full_name, args)
                if key == self.dedup_last_call.get(full_name):
                    return (True, "")
                self.dedup_last_call[full_name] = key
            return cast("tuple[bool, str]", await func(self, full_name, *args, **kwargs))

        return _wrapper

    return _remove_duplicates


class Pyprland:  # pylint: disable=too-many-instance-attributes
    """Main app object."""

    server: asyncio.Server
    event_reader: asyncio.StreamReader | None = None
    stopped = False
    config: dict[str, dict]
    tasks: list[asyncio.Task]
    tasks_group: None | asyncio.TaskGroup = None
    log_handler: Callable[[Plugin, str, tuple], None]
    dedup_last_call: dict[str, tuple[str, tuple[str, ...]]]
    _pyprland_conf: Configuration
    _shared_backend: EnvironmentBackend | None
    _backend_selected: bool
    state: SharedState

    def __init__(self) -> None:
        self.pyprland_mutex_event = asyncio.Event()
        self.pyprland_mutex_event.set()
        self.config = {}
        self.tasks = []
        self.plugins: dict[str, Plugin] = {}
        self.log = get_logger()
        self.queues: dict[str, asyncio.Queue] = {}
        self.dedup_last_call = {}
        self.state = SharedState()
        self._shared_backend: EnvironmentBackend | None = None
        self._backend_selected = False

        # Try socket-based detection first (sync)
        if os.environ.get("NIRI_SOCKET"):
            self.state.environment = "niri"
            self._shared_backend = NiriBackend(self.state)
            self._backend_selected = True
        elif os.environ.get("HYPRLAND_INSTANCE_SIGNATURE"):
            self.state.environment = "hyprland"
            self._shared_backend = HyprlandBackend(self.state)
            self._backend_selected = True
        else:
            # Fallback detection will happen in initialize() (async)
            # Use a temporary backend for early error notifications
            self._shared_backend = None

        # Manager's own proxy for notifications and event parsing
        # Will be updated in initialize() if fallback backend is selected
        if self._shared_backend:
            self.backend: BackendProxy = BackendProxy(self._shared_backend, self.log)
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    async def initialize(self) -> None:
        """Initialize the main structures."""
        # Complete backend selection if needed (fallback detection)
        if not self._backend_selected:
            await self._select_fallback_backend()

        try:
            await self.load_config()  # ensure sockets are connected first
        except KeyError as e:
            # Config file is invalid
            txt = f"Failed to load config, missing {e} section"
            self.log.critical(txt)
            await self.backend.notify_error(txt, duration=ERROR_NOTIFICATION_DURATION_MS)
            raise PyprError from e

    async def _select_fallback_backend(self) -> None:
        """Select a fallback backend when no socket-based environment is detected.

        Tries wlr-randr (Wayland) first, then xrandr (X11).
        """
        # Try generic Wayland (wlr-randr)
        if await WaylandBackend.is_available():
            self.state.environment = "wayland"
            self._shared_backend = WaylandBackend(self.state)
            self.log.info("Using generic Wayland backend (wlr-randr) - degraded mode")
        # Try X11 (xrandr)
        elif await XorgBackend.is_available():
            self.state.environment = "xorg"
            self._shared_backend = XorgBackend(self.state)
            self.log.info("Using X11/Xorg backend (xrandr) - degraded mode")
        else:
            # No backend available
            msg = "No supported environment detected"
            self.log.error("%s. Requires Hyprland, Niri, wlr-randr (Wayland), or xrandr (X11).", msg)
            raise RuntimeError(msg)

        self._backend_selected = True
        self.backend = BackendProxy(self._shared_backend, self.log)

    async def __open_config(self, config_filename: str = "") -> dict[str, Any]:
        """Load config file as self.config.

        Args:
            config_filename: Optional configuration file path
        """
        if config_filename:
            fname = os.path.expanduser(os.path.expandvars(config_filename))
            if os.path.isdir(fname):
                config: dict[str, Any] = {}
                for toml_file in sorted(os.listdir(fname)):
                    if not toml_file.endswith(".toml"):
                        continue
                    merge(config, self.__load_config_file(f"{fname}/{toml_file}"))
                return config
        else:
            if os.path.exists(OLD_CONFIG_FILE) and not os.path.exists(CONFIG_FILE):
                self.log.warning("Consider changing your configuration to TOML format.")
            fname = os.path.expanduser(os.path.expandvars(pyprland_constants.CONFIG_FILE))

        config = self.__load_config_file(fname)

        if not config_filename:
            for extra_config in list(config["pyprland"].get("include", [])):
                merge(config, await self.__open_config(extra_config))
            merge(self.config, config, replace=True)
        return config

    def __load_config_file(self, fname: str) -> dict[str, Any]:
        """Load a configuration file and returns it as a dictionary.

        Args:
            fname: Path to the configuration file
        """
        config = {}
        if os.path.exists(fname):
            self.log.info("Loading %s", fname)
            with open(fname, "rb") as f:
                try:
                    config = tomllib.load(f)
                except tomllib.TOMLDecodeError as e:
                    self.log.critical("Problem reading %s: %s", fname, e)
                    raise PyprError from e
        elif os.path.exists(os.path.expanduser(OLD_CONFIG_FILE)):
            self.log.info("Loading %s", OLD_CONFIG_FILE)
            with open(os.path.expanduser(OLD_CONFIG_FILE), encoding="utf-8") as f:
                config = json.loads(f.read())
        else:
            self.log.critical("Config file not found! Please create %s", fname)
            raise PyprError
        return config

    async def _load_single_plugin(self, name: str, init: bool) -> bool:
        """Load a single plugin, optionally calling `init`.

        Args:
            name: Plugin name
            init: Whether to initialize the plugin
        """
        if "." in name:
            modname = name
        elif "external:" in name:
            modname = name.replace("external:", "")
        else:
            modname = f"pyprland.plugins.{name}"
        try:
            plug = importlib.import_module(modname).Extension(name)
            desktop = self._pyprland_conf.get_str("desktop") or self.state.environment
            if plug.environments and desktop not in plug.environments:
                self.log.info("Skipping plugin %s: desktop %s not supported %s", name, desktop, plug.environments)
                return False
            plug.state = self.state
            # Each plugin gets its own BackendProxy with its own logger
            assert self._shared_backend is not None, "Backend not initialized"
            plug.backend = BackendProxy(self._shared_backend, plug.log)
            if init:
                await plug.init()
                self.queues[name] = asyncio.Queue()
                if self.tasks_group:
                    self.tasks_group.create_task(self._plugin_runner_loop(name))
            self.plugins[name] = plug
        except ModuleNotFoundError as e:
            self.log.exception("Unable to locate plugin called '%s'", name)
            await self.backend.notify_info(f'Config requires plugin "{name}" but pypr can\'t find it: {e}')
            return False
        except Exception as e:
            await self.backend.notify_info(f"Error loading plugin {name}: {e}")
            self.log.exception("Error loading plugin %s:", name)
            raise PyprError from e
        return True

    async def _init_plugin(self, name: str) -> None:
        """Initialize and configure a single plugin.

        Args:
            name: Plugin name
        """
        try:
            await self.plugins[name].load_config(self.config)
            # Validate configuration if plugin has a schema
            validation_errors = self.plugins[name].validate_config()
            for error in validation_errors:
                self.log.error(error)
            if validation_errors:
                await self.backend.notify_error(f"Plugin '{name}' has {len(validation_errors)} config error(s). Check logs for details.")
            await asyncio.wait_for(self.plugins[name].on_reload(), timeout=TASK_TIMEOUT / 2)
        except TimeoutError:
            self.plugins[name].log.info("timed out on reload")
        except Exception as e:
            await self.backend.notify_info(f"Error initializing plugin {name}: {e}")
            self.log.exception("Error initializing plugin %s:", name)
            raise PyprError from e
        else:
            self.plugins[name].log.info("configured")

    async def __load_plugins_config(self, init: bool = True) -> None:
        """Load the plugins mentioned in the config.

        If init is `True`, call the `init()` method on each plugin.

        Args:
            init: Whether to initialize the plugins
        """
        sys.path.extend(self.config["pyprland"].get("plugins_paths", []))

        init_pyprland = "pyprland" not in self.plugins

        current_plugins = set(self.plugins.keys())
        new_plugins = set(["pyprland"] + self.config["pyprland"]["plugins"])
        for name in current_plugins - new_plugins:
            self.log.info("Unloading plugin %s", name)
            plugin = self.plugins.pop(name)
            await plugin.exit()
            if name in self.queues:
                await self.queues.pop(name).put(None)

        for name in ["pyprland"] + self.config["pyprland"]["plugins"]:
            if name not in self.plugins and not await self._load_single_plugin(name, init):
                continue
            if init:
                await self._init_plugin(name)
        if init_pyprland:
            plug = self.plugins["pyprland"]
            plug.manager = self

    async def load_config(self, init: bool = True) -> None:
        """Load the configuration (new plugins will be added & config updated).

        if `init` is true, also initializes the plugins

        Args:
            init: Whether to initialize the plugins
        """
        await self.__open_config()
        assert self.config

        # Wrap pyprland section with schema for proper default handling
        self._pyprland_conf = Configuration(
            self.config.get("pyprland", {}),
            logger=self.log,
            schema=PYPRLAND_CONFIG_SCHEMA,
        )

        notification_type = self._pyprland_conf.get_str("notification_type")
        if notification_type and notification_type != "auto":
            set_notify_method(notification_type)

        await self.__load_plugins_config(init=init)

        # After plugins loaded, use the actual plugin's config (which has schema applied)
        colored_logs = self.plugins["pyprland"].config.get_bool("colored_handlers_log")
        self.log_handler = self.colored_log_handler if colored_logs else self.plain_log_handler

    def plain_log_handler(self, plugin: Plugin, name: str, params: tuple[str]) -> None:
        """Log a handler method without color.

        Args:
            plugin: The plugin instance
            name: The handler name
            params: Parameters passed to the handler
        """
        plugin.log.debug("%s%s", name, params)

    def colored_log_handler(self, plugin: Plugin, name: str, params: tuple[str]) -> None:
        """Log a handler method with color.

        Args:
            plugin: The plugin instance
            name: The handler name
            params: Parameters passed to the handler
        """
        style = HandlerStyles.COMMAND if name.startswith("run_") else HandlerStyles.EVENT
        plugin.log.debug(colorize(f"{name}{params}", *style))

    async def _run_plugin_handler(self, plugin: Plugin, full_name: str, params: tuple[str, ...]) -> tuple[bool, str]:
        """Run a single handler on a plugin.

        Args:
            plugin: The plugin instance
            full_name: The full name of the handler
            params: Parameters to pass to the handler

        Returns:
            A tuple of (success, message).
            On success: message contains handler return value (if string) or empty.
            On failure: message contains error description.
        """
        self.log_handler(plugin, full_name, params)
        try:
            handler = getattr(plugin, full_name)
            if inspect.iscoroutinefunction(handler):
                result = await handler(*params)
            else:
                result = handler(*params)
        except AssertionError as e:
            self.log.exception("This could be a bug in Pyprland, if you think so, report on https://github.com/fdev31/pyprland/issues")
            error_msg = f"Integrity check failed on {plugin.name}::{full_name}: {e}"
            await self.backend.notify_error(f"Pypr {error_msg}")
            return (False, error_msg)
        except Exception as e:  # pylint: disable=W0718
            self.log.exception("%s::%s(%s) failed:", plugin.name, full_name, params)
            error_msg = f"{plugin.name}::{full_name}: {e}"
            await self.backend.notify_error(f"Pypr error {error_msg}")
            if os.environ.get("PYPRLAND_STRICT_ERRORS"):
                raise
            return (False, error_msg)

        return_data = result if isinstance(result, str) else ""
        return (True, return_data)

    async def _run_plugin_handler_with_result(
        self, plugin: Plugin, full_name: str, params: tuple[str, ...], future: asyncio.Future[tuple[bool, str]]
    ) -> None:
        """Run handler and set result on future for queued commands.

        Args:
            plugin: The plugin instance
            full_name: The full name of the handler
            params: Parameters to pass to the handler
            future: Future to set result on
        """
        try:
            result = await self._run_plugin_handler(plugin, full_name, params)
            if not future.done():
                future.set_result(result)
        except Exception as e:  # pylint: disable=broad-exception-caught
            if not future.done():
                future.set_result((False, f"{plugin.name}::{full_name}: {e}"))

    async def _dispatch_to_plugin(self, plugin: Plugin, full_name: str, params: tuple[str, ...], wait: bool) -> tuple[bool, str]:
        """Dispatch a handler call to a non-pyprland plugin.

        Args:
            plugin: The plugin instance
            full_name: The full name of the handler
            params: Parameters to pass to the handler
            wait: If True, wait for handler completion

        Returns:
            A tuple of (success, message).
            On success: message contains handler return value (if string) or empty.
            On failure: message contains error description.
        """
        if wait:
            # Commands: queue and wait for result
            future: asyncio.Future[tuple[bool, str]] = asyncio.get_running_loop().create_future()
            cmd_task = partial(self._run_plugin_handler_with_result, plugin, full_name, params, future)
            await self.queues[plugin.name].put(cmd_task)
            try:
                success, msg = await asyncio.wait_for(future, timeout=TASK_TIMEOUT)
                return (success, msg)  # noqa: TRY300
            except TimeoutError:
                error_msg = f"{plugin.name}::{full_name}: Command timed out"
                self.log.exception(error_msg)
                return (False, error_msg)
        # Events: queue and continue (fire and forget)
        event_task = partial(self._run_plugin_handler, plugin, full_name, params)
        await self.queues[plugin.name].put(event_task)
        return (True, "")

    async def _handle_single_plugin(self, plugin: Plugin, full_name: str, params: tuple[str, ...], wait: bool) -> tuple[bool, str]:
        """Handle a single plugin's handler invocation.

        Args:
            plugin: The plugin instance
            full_name: The full name of the handler
            params: Parameters to pass to the handler
            wait: If True, wait for handler completion

        Returns:
            A tuple of (success, message).
        """
        if plugin.name == "pyprland":
            # pyprland plugin executes directly (built-in commands)
            return await self._run_plugin_handler(plugin, full_name, params)
        if not plugin.aborted:
            return await self._dispatch_to_plugin(plugin, full_name, params, wait)
        return (True, "")

    @remove_duplicate(names=["event_activewindow", "event_activewindowv2"])
    async def _call_handler(self, full_name: str, *params: str, notify: str = "", wait: bool = False) -> tuple[bool, bool, str]:
        """Call an event handler with params.

        Args:
            full_name: The full name of the handler
            *params: Parameters to pass to the handler
            notify: Notification message if handler not found
            wait: If True, wait for handler completion and return result (for commands)

        Returns:
            A tuple of (handled, success, message).
            - handled: True if at least one handler was found
            - success: True if all handlers succeeded (only meaningful when handled=True)
            - message: Error if failed, return data if succeeded (for commands with wait=True)
        """
        handled = False
        result_msg = ""
        error_msg = ""
        for plugin in self.plugins.values():
            if not hasattr(plugin, full_name):
                continue
            handled = True
            success, msg = await self._handle_single_plugin(plugin, full_name, params, wait)
            if success:
                if msg and not result_msg:
                    result_msg = msg
            elif not error_msg:
                error_msg = msg
        if notify and not handled:
            error_msg = f'Unknown command "{notify}". Try "help" for available commands.'
            await self.backend.notify_info(error_msg)
        # Return (handled, success, message)
        if error_msg:
            return (handled, False, error_msg)
        return (handled, True, result_msg)

    async def read_events_loop(self) -> None:
        """Consume the event loop and calls corresponding handlers."""
        if self.event_reader is None:
            return
        while not self.stopped:
            try:
                data = (await self.event_reader.readline()).decode(errors="replace")
            except RuntimeError:
                self.log.exception("Aborting event loop")
                return
            except UnicodeDecodeError:
                self.log.exception("Invalid unicode while reading events")
                continue
            if not data:
                self.log.critical("Reader starved")
                return

            parsed_event = self.backend.parse_event(data)
            if parsed_event:
                await self._call_handler(*parsed_event)

    async def exit_plugins(self) -> None:
        """Exit all plugins."""
        active_plugins = (p.exit() for p in self.plugins.values() if not p.aborted)
        await asyncio.wait_for(asyncio.gather(*active_plugins), timeout=TASK_TIMEOUT / 2)

    async def _abort_plugins(self, writer: asyncio.StreamWriter) -> None:
        """Abort all plugins and stop the server.

        Args:
            writer: The stream writer to close
        """
        await self.exit_plugins()
        # cancel the task group
        for task in self.tasks:
            task.cancel()
        writer.close()
        await writer.wait_closed()
        for q in self.queues.values():
            await q.put(None)
        self.server.close()
        # Ensure the process exits
        await asyncio.sleep(1)
        if os.path.exists(CONTROL):
            os.unlink(CONTROL)
        os._exit(0)

    async def _process_plugin_command(self, data: str) -> str:
        """Process a plugin command and return the response.

        Args:
            data: The command string

        Returns:
            Response string to send to client
        """
        args = data.split(None, 1)
        cmd = args[0]
        args = args[1:] if len(args) > 1 else []

        full_name = f"run_{cmd}"

        if PYPR_DEMO:
            os.system(f"notify-send -t {DEMO_NOTIFICATION_DURATION_MS} '{data}'")  # noqa: ASYNC221, S605

        handled, success, msg = await self._call_handler(full_name, *args, notify=cmd, wait=True)
        if not handled:
            self.log.warning("No such command: %s", cmd)
            return f"{ResponsePrefix.ERROR}: {msg}\n"
        if not success:
            return f"{ResponsePrefix.ERROR}: {msg}\n"
        # Success - msg contains return data (if any)
        if msg:
            return f"{ResponsePrefix.OK}\n{msg}"
        return f"{ResponsePrefix.OK}\n"

    async def _handle_exit_cleanup(self, writer: asyncio.StreamWriter) -> None:
        """Handle exit command cleanup after plugin dispatch.

        Args:
            writer: The stream writer
        """
        writer.write(f"{ResponsePrefix.OK}\n".encode())
        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
            await writer.drain()
        asyncio.create_task(self._abort_plugins(writer))

    async def read_command(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        """Receive a socket command.

        Args:
            reader: The stream reader
            writer: The stream writer
        """
        data = (await reader.readline()).decode()

        if not data:
            self.log.warning("Empty command received")
            writer.write(f"{ResponsePrefix.ERROR}: No command provided\n".encode())
        else:
            data = data.strip()
            response = await self._process_plugin_command(data)
            # Check if exit command was processed (sets self.stopped)
            if self.stopped:
                await self._handle_exit_cleanup(writer)
                return
            writer.write(response.encode())

        with contextlib.suppress(BrokenPipeError, ConnectionResetError):
            await writer.drain()
        writer.close()

    async def serve(self) -> None:
        """Run the server."""
        async with self.server:
            await self.server.wait_closed()

    async def _execute_queued_task(self, name: str, task: partial) -> None:
        """Execute a single queued task with timeout and error handling.

        Args:
            name: Plugin name for logging
            task: The task to execute
        """
        try:
            await asyncio.wait_for(task(), timeout=TASK_TIMEOUT)
        except asyncio.CancelledError:
            self.log.warning("Task cancelled for plugin %s", name)
        except TimeoutError:
            self.log.exception("Timeout running plugin %s::%s", name, task)
        except Exception:  # pylint: disable=W0718
            self.log.exception("Unhandled error running plugin %s::%s", name, task)
            if os.environ.get("PYPRLAND_STRICT_ERRORS"):
                raise

    async def _plugin_runner_loop(self, name: str) -> None:
        """Run tasks for a given plugin indefinitely.

        Args:
            name: Plugin name
        """
        q = self.queues[name]
        is_pyprland = name == "pyprland"

        while not self.stopped:
            if not is_pyprland:
                await self.pyprland_mutex_event.wait()
            try:
                task = await q.get()
                if task is None:
                    return
                if is_pyprland:
                    self.pyprland_mutex_event.clear()
            except RuntimeError:
                self.log.exception("Aborting [%s] loop", name)
                return
            await self._execute_queued_task(name, task)
            if is_pyprland and q.empty():
                self.pyprland_mutex_event.set()

    async def plugins_runner(self) -> None:
        """Run plugins' task using the created `tasks` TaskGroup attribute."""
        async with asyncio.TaskGroup() as group:
            self.tasks_group = group
            for name in self.plugins:
                self.tasks.append(group.create_task(self._plugin_runner_loop(name)))

    async def run(self) -> None:
        """Run the server and the event listener."""
        tasks = [
            asyncio.create_task(self.serve()),
            asyncio.create_task(self.plugins_runner()),
        ]
        if self.event_reader:
            tasks.append(asyncio.create_task(self.read_events_loop()))
        await asyncio.gather(*tasks)
