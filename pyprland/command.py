#!/bin/env python
""" Pyprland - an Hyprland companion app (cli client & daemon) """
import asyncio
import importlib
import itertools
import tomllib
import json
import os
import sys
from typing import cast
from collections import defaultdict

from .common import PyprError, get_logger, init_logger
from .ipc import get_event_stream
from .ipc import init as ipc_init
from .plugins.interface import Plugin

CONTROL = f'/tmp/hypr/{ os.environ["HYPRLAND_INSTANCE_SIGNATURE"] }/.pyprland.sock'

OLD_CONFIG_FILE = "~/.config/hypr/pyprland.json"
CONFIG_FILE = "~/.config/hypr/pyprland.toml"


class Pyprland:
    "Main app object"
    server: asyncio.Server
    event_reader: asyncio.StreamReader
    stopped = False
    name = "builtin"
    config: None | dict[str, dict] = None

    def __init__(self):
        self.plugins: dict[str, Plugin] = {}
        self.log = get_logger()

    async def load_config(self, init=True):
        """Loads the configuration

        if `init` is true, also initializes the plugins"""
        if os.path.exists(OLD_CONFIG_FILE) and not os.path.exists(CONFIG_FILE):
            self.log.warning("Consider changing your configuration to TOML format.")

        fname = os.path.expanduser(CONFIG_FILE)
        if os.path.exists(fname):
            self.log.info("Loading %s", fname)
            try:
                with open(fname, "rb") as f:
                    self.config = tomllib.load(f)
            except FileNotFoundError as e:
                self.log.critical(
                    "No config file found, create one at ~/.config/hypr/pyprland.json with a valid pyprland.plugins list"
                )
                raise PyprError() from e
        elif os.path.exists(os.path.expanduser(OLD_CONFIG_FILE)):
            self.log.info("Loading %s", OLD_CONFIG_FILE)
            try:
                with open(os.path.expanduser(OLD_CONFIG_FILE), encoding="utf-8") as f:
                    self.config = json.loads(f.read())
            except FileNotFoundError as e:
                self.log.critical(
                    "No config file found, create one at ~/.config/hypr/pyprland.json with a valid pyprland.plugins list"
                )
                raise PyprError() from e
        else:
            self.log.critical("No Config file found ! Please create %s" % CONFIG_FILE)
            raise PyprError()

        assert self.config

        for name in cast(dict, self.config["pyprland"]["plugins"]):
            if name not in self.plugins:
                modname = name if "." in name else f"pyprland.plugins.{name}"
                try:
                    plug = importlib.import_module(modname).Extension(name)
                    if init:
                        await plug.init()
                    self.plugins[name] = plug
                except ModuleNotFoundError:
                    self.log.error("Unable to locate plugin called '%s'", name)
                    continue
                except Exception as e:
                    self.log.error("Error loading plugin %s:", name, exc_info=True)
                    raise PyprError() from e
            if init:
                try:
                    await self.plugins[name].load_config(self.config)
                except PyprError:
                    raise
                except Exception as e:
                    self.log.error("Error initializing plugin %s:", name, exc_info=True)
                    raise PyprError() from e

    async def _callHandler(self, full_name, *params):
        "Call an event handler with params"

        for plugin in [self] + list(self.plugins.values()):
            if hasattr(plugin, full_name):
                self.log.debug("%s.%s%s", plugin.name, full_name, params)
                try:
                    await getattr(plugin, full_name)(*params)
                except AssertionError as e:
                    self.log.error(
                        "Bug detected, please report on https://github.com/fdev31/pyprland/issues"
                    )
                    self.log.exception(e)
                except Exception as e:  # pylint: disable=W0718
                    self.log.warning(
                        "%s::%s(%s) failed:", plugin.name, full_name, params
                    )
                    self.log.exception(e)
                break
        else:
            return False
        return True

    async def read_events_loop(self):
        "Consumes the event loop and calls corresponding handlers"
        last_cmd_args: dict[str, None | str] = defaultdict(lambda: None)
        while not self.stopped:
            try:
                data = (await self.event_reader.readline()).decode()
            except UnicodeDecodeError:
                self.log.error("Invalid unicode while reading events")
                continue
            if not data:
                self.log.critical("Reader starved")
                return
            cmd, params = data.split(">>", 1)
            last_args = last_cmd_args.get(cmd)
            if params != last_args:
                full_name = f"event_{cmd}"

                # self.log.debug("[%s] %s", cmd, params.strip())
                await self._callHandler(full_name, params)
            last_cmd_args[cmd] = params

    async def read_command(self, reader, writer) -> None:
        "Receives a socket command"
        data = (await reader.readline()).decode()
        if not data:
            self.log.critical("Server starved")
            return
        if data == "exit\n":
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
        # Demos:
        # run mako for notifications & uncomment this
        # os.system(f"notify-send '{data}'")

        if not await self._callHandler(full_name, *args):
            self.log.warning("No such command: %s", cmd)

    async def serve(self):
        "Runs the server"
        try:
            async with self.server:
                await self.server.serve_forever()
        finally:
            await asyncio.gather(*(plugin.exit() for plugin in self.plugins.values()))

    async def run(self):
        "Runs the server and the event listener"
        await asyncio.gather(
            asyncio.create_task(self.serve()),
            asyncio.create_task(self.read_events_loop()),
        )

    run_reload = load_config


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
                raise PyprError() from e
            manager.log.warning(
                "Failed to get event stream: %s}, retry %s/%s...", e, attempt, max_retry
            )
            await asyncio.sleep(1)
        else:
            break

    manager.event_reader = events_reader

    try:
        await manager.load_config()  # ensure sockets are connected first
    except PyprError as e:
        raise SystemExit(1) from e
    except Exception as e:
        manager.log.critical("Failed to load config.", exc_info=True)
        raise SystemExit(1) from e

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
    if sys.argv[1] in ("--help", "-h", "help"):
        await manager.load_config(init=False)
        print(
            """Syntax: pypr [command]

If command is ommited, runs the daemon which will start every configured command.

Commands:

 reload               Reloads the config file (only supports adding or updating plugins)"""
        )
        for plug in manager.plugins.values():
            for name in dir(plug):
                if name.startswith("run_"):
                    fn = getattr(plug, name)
                    if callable(fn):
                        print(
                            f" {name[4:]:20} {fn.__doc__.strip() if fn.__doc__ else 'N/A'} (from {plug.name})"
                        )

        return

    try:
        _, writer = await asyncio.open_unix_connection(CONTROL)
    except (ConnectionRefusedError, FileNotFoundError) as e:
        manager.log.critical("Failed to open control socket, is pypr daemon running ?")
        raise PyprError() from e

    writer.write((" ".join(sys.argv[1:])).encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()


def main():
    "runs the command"
    if "--debug" in sys.argv:
        i = sys.argv.index("--debug")
        init_logger(filename=sys.argv[i + 1], force_debug=True)
        del sys.argv[i : i + 2]
    else:
        init_logger()
    ipc_init()
    log = get_logger("startup")
    try:
        asyncio.run(run_daemon() if len(sys.argv) <= 1 else run_client())
    except KeyboardInterrupt:
        pass
    except PyprError:
        log.critical("Command failed.")
    except json.decoder.JSONDecodeError as e:
        log.critical("Invalid JSON syntax in the config file: %s", e.args[0])
    except Exception:  # pylint: disable=W0718
        log.critical("Unhandled exception:", exc_info=True)


if __name__ == "__main__":
    main()
