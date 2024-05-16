"""Pyprland - an Hyprland companion app (cli client & daemon)."""

import asyncio
import importlib
import itertools
import json
import os
import sys
import tomllib
from collections.abc import Callable
from functools import partial
from typing import Any, Self

from pyprland.common import IPC_FOLDER, get_logger, init_logger, merge, run_interactive_program
from pyprland.ipc import get_event_stream, notify_error, notify_fatal, notify_info
from pyprland.ipc import init as ipc_init
from pyprland.plugins.interface import Plugin
from pyprland.types import PyprError
from pyprland.version import VERSION

CONTROL = f"{IPC_FOLDER}/.pyprland.sock"
OLD_CONFIG_FILE = "~/.config/hypr/pyprland.json"
CONFIG_FILE = "~/.config/hypr/pyprland.toml"

PYPR_DEMO = os.environ.get("PYPR_DEMO", False)

__all__: list[str] = []


class Pyprland:
    """Main app object."""

    server: asyncio.Server
    event_reader: asyncio.StreamReader
    stopped = False
    config: dict[str, dict] = {}
    tasks: list[asyncio.Task] = []
    tasks_group: None | asyncio.TaskGroup = None
    instance: Self | None = None
    log_handler: Callable[[Plugin, str, tuple], None]

    @classmethod
    def _set_instance(cls, instance) -> None:
        """Set instance reference into class (for testing/debugging only)."""
        cls.instance = instance

    def __init__(self) -> None:
        self.pyprland_mutex_event = asyncio.Event()
        self.pyprland_mutex_event.set()
        self.config = {}
        self.plugins: dict[str, Plugin] = {}
        self.log = get_logger()
        self.queues: dict[str, asyncio.Queue] = {}
        self._set_instance(self)

    async def initialize(self) -> None:
        """Initialize the main structures."""
        await self.load_config()  # ensure sockets are connected first

    async def __open_config(self, config_filename=""):
        """Load config file as self.config."""
        if config_filename:
            fname = os.path.expandvars(os.path.expanduser(config_filename))
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
            self.config.clear()
            fname = os.path.expanduser(CONFIG_FILE)

        config = self.__load_config_file(fname)

        if not config_filename:
            for extra_config in list(config["pyprland"].get("include", [])):
                merge(config, await self.__open_config(extra_config))
            self.config.update(config)
        return config

    def __load_config_file(self, fname):
        """Load a configuration file and returns it as a dictionary."""
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

    async def _load_single_plugin(self, name, init) -> bool:
        """Load a single plugin, optionally calling `init`."""
        if "." in name:
            modname = name
        elif "external:" in name:
            modname = name.replace("external:", "")
        else:
            modname = f"pyprland.plugins.{name}"
        try:
            plug = importlib.import_module(modname).Extension(name)
            if init:
                await plug.init()
                self.queues[name] = asyncio.Queue()
                if self.tasks_group:
                    self.tasks_group.create_task(self._plugin_runner_loop(name))
            self.plugins[name] = plug
        except ModuleNotFoundError as e:
            self.log.error("Unable to locate plugin called '%s'", name)
            await notify_info(f'Config requires plugin "{name}" but pypr can\'t find it: {e}')
            return False
        except Exception as e:
            await notify_info(f"Error loading plugin {name}: {e}")
            self.log.error("Error loading plugin %s:", name, exc_info=True)
            raise PyprError from e
        return True

    async def __load_plugins_config(self, init=True) -> None:
        """Load the plugins mentioned in the config.

        If init is `True`, call the `init()` method on each plugin.
        """
        sys.path.extend(self.config["pyprland"].get("plugins_paths", []))

        init_pyprland = "pyprland" not in self.plugins

        for name in ["pyprland"] + self.config["pyprland"]["plugins"]:
            if name not in self.plugins and not await self._load_single_plugin(name, init):
                continue
            if init:
                try:
                    await self.plugins[name].load_config(self.config)
                    await asyncio.wait_for(self.plugins[name].on_reload(), timeout=5.0)
                except TimeoutError:
                    self.plugins[name].log.info("timed out on reload")
                except PyprError:
                    raise
                except Exception as e:
                    await notify_info(f"Error initializing plugin {name}: {e}")
                    self.log.error("Error initializing plugin %s:", name, exc_info=True)
                    raise PyprError from e
                else:
                    self.plugins[name].log.info("configured")
        if init_pyprland:
            plug = self.plugins["pyprland"]
            plug.set_commands(reload=self.load_config)  # type: ignore

    async def load_config(self, init=True) -> None:
        """Load the configuration (new plugins will be added & config updated).

        if `init` is true, also initializes the plugins
        """
        await self.__open_config()
        assert self.config
        await self.__load_plugins_config(init=init)
        colored_logs = self.config["pyprland"].get("colored_handlers_log", True)
        self.log_handler = self.colored_log_handler if colored_logs else self.plain_log_handler

    def plain_log_handler(self, plugin, name, params) -> None:
        """Log a handler method without color."""
        plugin.log.debug(f"{name}{params}")

    def colored_log_handler(self, plugin, name, params) -> None:
        """Log a handler method with color."""
        color = 33 if name.startswith("run_") else 30
        plugin.log.debug(f"\033[{color};1m%s%s\033[0m", name, params)

    async def _run_plugin_handler(self, plugin, full_name, params) -> None:
        """Run a single handler on a plugin."""
        self.log_handler(plugin, full_name, params)
        try:
            await getattr(plugin, full_name)(*params)
        except AssertionError as e:
            self.log.error("This could be a bug in Pyprland, if you think so, report on https://github.com/fdev31/pyprland/issues")
            self.log.exception(e)
            await notify_error(f"Pypr integrity check failed on {plugin.name}::{full_name}: {e}")
        except Exception as e:  # pylint: disable=W0718
            self.log.warning("%s::%s(%s) failed:", plugin.name, full_name, params)
            self.log.exception(e)
            await notify_error(f"Pypr error {plugin.name}::{full_name}: {e}")

    async def _call_handler(self, full_name, *params, notify=""):
        """Call an event handler with params."""
        handled = False
        for plugin in self.plugins.values():
            if hasattr(plugin, full_name):
                handled = True
                task = partial(self._run_plugin_handler, plugin, full_name, params)
                if plugin == "pyprland":
                    await task()
                elif not plugin.aborted:
                    await self.queues[plugin.name].put(task)
        if notify and not handled:
            await notify_info(f'"{notify}" not found')
        return handled

    async def read_events_loop(self) -> None:
        """Consume the event loop and calls corresponding handlers."""
        while not self.stopped:
            try:
                data = (await self.event_reader.readline()).decode()
            except RuntimeError as e:
                self.log.error("Aborting event loop: %s", e)
                return
            except UnicodeDecodeError:
                self.log.error("Invalid unicode while reading events")
                continue
            if not data:
                self.log.critical("Reader starved")
                return
            cmd, params = data.split(">>", 1)
            full_name = f"event_{cmd}"

            # self.log.debug("[%s] %s", cmd, params.strip())
            await self._call_handler(full_name, params.rstrip("\n"))

    async def exit_plugins(self) -> None:
        """Exit all plugins."""
        for plugin in self.plugins.values():
            if not plugin.aborted:
                plugin.aborted = True
                await asyncio.wait_for(plugin.exit(), timeout=2.0)

    async def read_command(self, reader, writer) -> None:
        """Receive a socket command."""
        data = (await reader.readline()).decode()
        if not data:
            self.log.critical("Server starved")
            data = "exit"
        data = data.strip()
        if data == "exit":

            async def _abort() -> None:
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

            self.stopped = True
            asyncio.create_task(_abort())
            return
        args = data.split(None, 1)
        if len(args) == 1:
            cmd = args[0]
            args = []
        else:
            cmd = args[0]
            args = args[1:]

        full_name = f"run_{cmd}"

        if PYPR_DEMO:
            os.system(f"notify-send -t 4000 '{data}'")  # noqa: ASYNC102

        if not await self._call_handler(full_name, *args, notify=cmd):
            self.log.warning("No such command: %s", cmd)

    async def serve(self) -> None:
        """Run the server."""
        async with self.server:
            await self.server.wait_closed()

    async def _plugin_runner_loop(self, name) -> None:
        """Run tasks for a given plugin indefinitely."""
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
            except RuntimeError as e:
                self.log.error("Aborting [%s] loop: %s", name, e)
                return
            try:
                await asyncio.wait_for(task(), timeout=12.0)
            except TimeoutError:
                self.log.error("Timeout running plugin %s::%s", name, task)
            except Exception as e:  # pylint: disable=W0718
                self.log.error("Unhandled error running plugin %s::%s: %s", name, task, e)
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
        await asyncio.gather(
            asyncio.create_task(self.serve()),
            asyncio.create_task(self.read_events_loop()),
            asyncio.create_task(self.plugins_runner()),
        )


async def get_event_stream_with_retry(max_retry=10):
    """Obtain the event stream, retrying if it fails.

    If retry count is exhausted, returns (None, exception).
    """
    err_count = itertools.count()
    while True:
        attempt = next(err_count)
        try:
            return await get_event_stream()
        except Exception as e:  # pylint: disable=W0718
            if attempt > max_retry:
                return None, e
            await asyncio.sleep(1)


async def run_daemon() -> None:
    """Run the server / daemon."""
    manager = Pyprland()
    manager.server = await asyncio.start_unix_server(manager.read_command, CONTROL)

    events_reader, events_writer = await get_event_stream_with_retry()
    if not events_reader:
        manager.log.critical("Failed to open hyprland event stream: %s.", events_writer)
        await notify_fatal("Failed to open hyprland event stream")
        raise PyprError from events_writer

    manager.event_reader = events_reader

    await manager.initialize()

    manager.log.debug("[ initialized ]".center(80, "="))

    try:
        await manager.run()
    except KeyboardInterrupt:
        print("Interrupted")
    except asyncio.CancelledError:
        manager.log.critical("cancelled")
    else:
        await manager.exit_plugins()
        events_writer.close()
        await events_writer.wait_closed()
        manager.server.close()
        await manager.server.wait_closed()


def show_help(manager) -> None:
    """Show the documentation."""

    def format_doc(txt):
        return txt.split("\n")[0]

    print(
        """Syntax: pypr [command]

If the command is ommited, runs the daemon which will start every configured plugin.

Available commands:
"""
    )
    builtins_docs = {
        "dumpjson": "Dump the configuration in JSON format.",
        "edit": "Edit the configuration file.",
        "exit": "Exit the daemon.",
        "help": "Show this help.",
        "version": "Show the version.",
    }
    for name, doc in builtins_docs.items():
        print(f" {name:20s} {doc}")

    for plug in manager.plugins.values():
        for name in dir(plug):
            if not name.startswith("run_"):
                continue
            fn = getattr(plug, name)
            if callable(fn):
                doc_txt = format_doc(fn.__doc__) if fn.__doc__ else "N/A"
                print(f" {name[4:]:20s} {doc_txt} [{plug.name}]")


async def run_client():
    """Run the client (CLI)."""
    manager = Pyprland()

    if sys.argv[1] == "version":
        print(VERSION)
        return None

    if sys.argv[1] == "edit":
        editor = os.environ.get("EDITOR", os.environ.get("VISUAL", "vi"))
        filename = os.path.expanduser(CONFIG_FILE)
        run_interactive_program(f'{editor} "{filename}"')
        sys.argv[1] = "reload"

    if sys.argv[1] in {"--help", "-h", "help"}:
        await manager.load_config(init=False)
        return show_help(manager)

    if sys.argv[1] in ("dumpjson"):
        await manager.load_config(init=False)
        # Dump manager.config in TOML format
        print(json.dumps(manager.config, indent=2))
        return None

    try:
        _, writer = await asyncio.open_unix_connection(CONTROL)
    except (ConnectionRefusedError, FileNotFoundError) as e:
        manager.log.critical("Failed to open control socket, is pypr daemon running ?")
        await notify_error("Pypr can't connect, is daemon running ?")
        raise PyprError from e

    args = sys.argv[1:]
    args[0] = args[0].replace("-", "_")
    writer.write((" ".join(args)).encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()


def use_param(txt):
    """Check if parameter `txt` is in sys.argv.

    if found, removes it from sys.argv & returns the argument value
    """
    v = ""
    if txt in sys.argv:
        i = sys.argv.index(txt)
        v = sys.argv[i + 1]
        del sys.argv[i : i + 2]
    return v


def main() -> None:
    """Run the command."""
    debug_flag = use_param("--debug")
    if debug_flag:
        init_logger(filename=debug_flag, force_debug=True)
    else:
        init_logger()
    ipc_init()
    log = get_logger("startup")

    config_override = use_param("--config")
    if config_override:
        global CONFIG_FILE
        CONFIG_FILE = config_override

    invoke_daemon = len(sys.argv) <= 1
    if invoke_daemon and os.path.exists(CONTROL):
        asyncio.run(notify_fatal("Trying to run pypr more than once ?"))
        log.critical(
            """%s exists,
is pypr already running ?
If that's not the case, delete this file and run again.""",
            CONTROL,
        )
    else:
        try:
            asyncio.run(run_daemon() if invoke_daemon else run_client())
        except KeyboardInterrupt:
            pass
        except PyprError:
            log.critical("Command failed.")
        except json.decoder.JSONDecodeError as e:
            log.critical("Invalid JSON syntax in the config file: %s", e.args[0])
        except Exception:  # pylint: disable=W0718
            log.critical("Unhandled exception:", exc_info=True)
        finally:
            if invoke_daemon and os.path.exists(CONTROL):
                os.unlink(CONTROL)


if __name__ == "__main__":
    main()
