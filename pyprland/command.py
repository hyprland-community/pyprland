#!/bin/env python
""" Pyprland - an Hyprland companion app (cli client & daemon) """
import asyncio
import importlib
import itertools
from functools import partial
from typing import Self
import tomllib
import json
import os
import sys

from pyprland.common import PyprError, get_logger, init_logger
from pyprland.ipc import get_event_stream, notify_error, notify_fatal, notify_info
from pyprland.ipc import init as ipc_init
from pyprland.plugins.interface import Plugin

try:
    CONTROL = f'/tmp/hypr/{ os.environ["HYPRLAND_INSTANCE_SIGNATURE"] }/.pyprland.sock'
except KeyError:
    print(
        "This is a fatal error, assuming we are running documentation generation hence ignoring it"
    )

OLD_CONFIG_FILE = "~/.config/hypr/pyprland.json"
CONFIG_FILE = "~/.config/hypr/pyprland.toml"

PYPR_DEMO = os.environ.get("PYPR_DEMO", False)

__all__: list[str] = []


class Pyprland:
    "Main app object"
    server: asyncio.Server
    event_reader: asyncio.StreamReader
    stopped = False
    config: dict[str, dict] = {}
    tasks: None | asyncio.TaskGroup = None
    instance: Self | None = None

    @classmethod
    def _set_instance(cls, instance):
        "Set instance reference into class (for testing/debugging only)"
        cls.instance = instance

    def __init__(self):
        self.config = {}
        self.plugins: dict[str, Plugin] = {}
        self.log = get_logger()
        self.queues = {}
        self._set_instance(self)

    async def initialize(self):
        "Initializes the main structures"
        await self.load_config()  # ensure sockets are connected first

    async def __open_config(self):
        """Loads config file as self.config"""
        if os.path.exists(OLD_CONFIG_FILE) and not os.path.exists(CONFIG_FILE):
            self.log.warning("Consider changing your configuration to TOML format.")

        self.config.clear()
        fname = os.path.expanduser(CONFIG_FILE)
        if os.path.exists(fname):
            self.log.info("Loading %s", fname)
            try:
                with open(fname, "rb") as f:
                    self.config.update(tomllib.load(f))
            except FileNotFoundError as e:
                self.log.critical(
                    "No config file found, create one at ~/.config/hypr/pyprland.json with a valid pyprland.plugins list"
                )
                raise PyprError() from e
        elif os.path.exists(os.path.expanduser(OLD_CONFIG_FILE)):
            self.log.info("Loading %s", OLD_CONFIG_FILE)
            try:
                with open(os.path.expanduser(OLD_CONFIG_FILE), encoding="utf-8") as f:
                    self.config.update(json.loads(f.read()))
            except FileNotFoundError as e:
                self.log.critical(
                    "No config file found, create one at ~/.config/hypr/pyprland.json with a valid pyprland.plugins list"
                )
                raise PyprError() from e
        else:
            self.log.critical("No Config file found ! Please create %s", CONFIG_FILE)
            raise PyprError()

    async def __load_plugins_config(self, init=True):
        """Loads the plugins mentioned in the config.
        If init is `True`, call the `init()` method on each plugin.
        """
        init_pyprland = "pyprland" not in self.plugins
        for name in ["pyprland"] + self.config["pyprland"]["plugins"]:
            if name not in self.plugins:
                modname = name if "." in name else f"pyprland.plugins.{name}"
                try:
                    plug = importlib.import_module(modname).Extension(name)
                    if init:
                        await plug.init()
                        self.queues[name] = asyncio.Queue()
                        if self.tasks:
                            self.tasks.create_task(self._plugin_runner_loop(name))
                    self.plugins[name] = plug
                except ModuleNotFoundError as e:
                    self.log.error("Unable to locate plugin called '%s'", name)
                    await notify_info(
                        f'Config requires plugin "{name}" but pypr can\'t find it: {e}'
                    )
                    continue
                except Exception as e:
                    await notify_info(f"Error loading plugin {name}: {e}")
                    self.log.error("Error loading plugin %s:", name, exc_info=True)
                    raise PyprError() from e
            if init:
                try:
                    await self.plugins[name].load_config(self.config)
                    await self.plugins[name].on_reload()
                    self.plugins[name].log.info("configured")
                except PyprError:
                    raise
                except Exception as e:
                    await notify_info(f"Error initializing plugin {name}: {e}")
                    self.log.error("Error initializing plugin %s:", name, exc_info=True)
                    raise PyprError() from e
        if init_pyprland:
            plug = self.plugins["pyprland"]
            plug.set_commands(reload=self.load_config)

    async def load_config(self, init=True):
        """loads the configuration (new plugins will be added & config updated)

        if `init` is true, also initializes the plugins"""

        await self.__open_config()
        assert self.config
        await self.__load_plugins_config(init=init)
        if self.config["pyprland"].get("colored_handlers_log", True):
            self.log_handler = (  # pylint: disable=attribute-defined-outside-init
                self.colored_log_handler
            )
        else:
            self.log_handler = (  # pylint: disable=attribute-defined-outside-init
                self.plain_log_handler
            )

    def plain_log_handler(self, plugin, name, params):
        "log a handler method without color"
        plugin.log.debug(f"{name}{params}")

    def colored_log_handler(self, plugin, name, params):
        "log a handler method with color"
        color = 33 if name.startswith("run_") else 30
        plugin.log.debug(f"\033[{color};1m%s%s\033[0m", name, params)

    async def _run_plugin_handler(self, plugin, full_name, params):
        "Runs a single handler on a plugin"
        self.log_handler(plugin, full_name, params)
        try:
            await getattr(plugin, full_name)(*params)
        except AssertionError as e:
            self.log.error(
                "This could be a bug in Pyprland, if you think so, report on https://github.com/fdev31/pyprland/issues"
            )
            self.log.exception(e)
            await notify_error(
                f"Pypr integrity check failed on {plugin.name}::{full_name}: {e}"
            )
        except Exception as e:  # pylint: disable=W0718
            self.log.warning("%s::%s(%s) failed:", plugin.name, full_name, params)
            self.log.exception(e)
            await notify_error(f"Pypr error {plugin.name}::{full_name}: {e}")

    async def _callHandler(self, full_name, *params, notify=""):
        "Call an event handler with params"
        handled = False
        for plugin in self.plugins.values():
            if hasattr(plugin, full_name):
                handled = True
                task = partial(self._run_plugin_handler, plugin, full_name, params)
                if plugin == "pyprland":
                    await task()
                else:
                    await self.queues[plugin.name].put(task)
        if notify and not handled:
            await notify_info(f'"{notify}" not found')
        return handled

    async def read_events_loop(self):
        "Consumes the event loop and calls corresponding handlers"
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
            await self._callHandler(full_name, params.rstrip("\n"))

    async def read_command(self, reader, writer) -> None:
        "Receives a socket command"
        data = (await reader.readline()).decode()
        if not data:
            self.log.critical("Server starved")
            data = "exit"
        data = data.strip()
        if data == "exit":
            self.stopped = True
            writer.close()
            await writer.wait_closed()
            self.server.close()
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
            os.system(f"notify-send -t 4000 '{data}'")

        if not await self._callHandler(full_name, *args, notify=cmd):
            self.log.warning("No such command: %s", cmd)

    async def serve(self):
        "Runs the server"
        try:
            async with self.server:
                await self.server.serve_forever()
        finally:
            await asyncio.gather(*(plugin.exit() for plugin in self.plugins.values()))

    async def _plugin_runner_loop(self, name):
        "Runs tasks for a given plugin indefinitely"
        q = self.queues[name]

        while not self.stopped:
            try:
                task = await q.get()
            except RuntimeError as e:
                self.log.error("Aborting [%s] loop: %s", name, e)
                return
            try:
                await task()
            except Exception as e:  # pylint: disable=W0718
                self.log.error(
                    "Unhandled error running plugin %s::%s: %s", name, task, e
                )

    async def plugins_runner(self):
        "Runs plugins' task using the created `tasks` TaskGroup attribute"
        async with asyncio.TaskGroup() as group:
            self.tasks = group
            for name in self.plugins:
                group.create_task(self._plugin_runner_loop(name))

    async def run(self):
        "Runs the server and the event listener"
        await asyncio.gather(
            asyncio.create_task(self.serve()),
            asyncio.create_task(self.read_events_loop()),
            asyncio.create_task(self.plugins_runner()),
        )


async def run_daemon():
    "Runs the server / daemon"
    manager = Pyprland()
    err_count = itertools.count()
    manager.server = await asyncio.start_unix_server(manager.read_command, CONTROL)
    max_retry = 10
    while True:
        attempt = next(err_count)
        try:
            events_reader, events_writer = await get_event_stream()
        except Exception as e:  # pylint: disable=W0718
            if attempt > max_retry:
                manager.log.critical("Failed to open hyprland event stream: %s.", e)
                await notify_fatal("Failed to open hyprland event stream")
                raise PyprError() from e
            manager.log.warning(
                "Failed to get event stream: %s, retry %s/%s...", e, attempt, max_retry
            )
            await asyncio.sleep(1)
        else:
            break

    manager.event_reader = events_reader

    try:
        await manager.initialize()
    except PyprError as e:
        if bool(str(e)):
            await notify_fatal(f"Pypr failed to start: {e}")
        else:
            await notify_fatal("Pypr failed to start!")

        raise SystemExit(1) from e
    except Exception as e:
        manager.log.critical("Failed to load config.", exc_info=True)
        await notify_fatal(f"Pypr couldn't load config: {e}")
        raise SystemExit(1) from e

    manager.log.debug("[ initialized ]".center(80, "="))
    try:
        await manager.run()
    except KeyboardInterrupt:
        print("Interrupted")
    except asyncio.CancelledError:
        manager.log.critical("cancelled")
    finally:
        events_writer.close()
        await events_writer.wait_closed()
        manager.server.close()
        await manager.server.wait_closed()


async def run_client():
    "Runs the client (CLI)"
    manager = Pyprland()

    if sys.argv[1] == "version":
        print("2.0.9-5-g82723be")  # Automatically updated version
        return

    if sys.argv[1] in ("--help", "-h", "help"):
        await manager.load_config(init=False)

        def format_doc(txt):
            return txt.split("\n")[0]

        print(
            """Syntax: pypr [command]

If the command is ommited, runs the daemon which will start every configured plugin.

Available commands:
"""
        )
        for plug in manager.plugins.values():
            for name in dir(plug):
                if name.startswith("run_"):
                    fn = getattr(plug, name)
                    if callable(fn):
                        print(
                            f" {name[4:]:20s} {format_doc(fn.__doc__) if fn.__doc__ else 'N/A'} [{plug.name}]"
                        )

        return

    try:
        _, writer = await asyncio.open_unix_connection(CONTROL)
    except (ConnectionRefusedError, FileNotFoundError) as e:
        manager.log.critical("Failed to open control socket, is pypr daemon running ?")
        await notify_error("Pypr can't connect, is daemon running ?")
        raise PyprError() from e

    args = sys.argv[1:]
    args[0] = args[0].replace("-", "_")
    writer.write((" ".join(args)).encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()


def use_param(txt):
    """Checks if parameter `txt` is in sys.argv
    if found, removes it from sys.argv & returns the argument value
    """
    v = ""
    if txt in sys.argv:
        i = sys.argv.index(txt)
        v = sys.argv[i + 1]
        del sys.argv[i : i + 2]
    return v


def main():
    "runs the command"
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
            if invoke_daemon:
                os.unlink(CONTROL)


if __name__ == "__main__":
    main()
