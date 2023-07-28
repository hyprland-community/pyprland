#!/bin/env python
import asyncio
import json
import sys
import os
import importlib
import itertools
import traceback


from .ipc import get_event_stream
from .common import DEBUG
from .plugins.interface import Plugin

CONTROL = f'/tmp/hypr/{ os.environ["HYPRLAND_INSTANCE_SIGNATURE"] }/.pyprland.sock'

CONFIG_FILE = "~/.config/hypr/pyprland.json"


class Pyprland:
    server: asyncio.Server
    event_reader: asyncio.StreamReader
    stopped = False
    name = "builtin"

    def __init__(self):
        self.plugins: dict[str, Plugin] = {}

    async def load_config(self, init=True):
        self.config = json.loads(
            open(os.path.expanduser(CONFIG_FILE), encoding="utf-8").read()
        )
        for name in self.config["pyprland"]["plugins"]:
            if name not in self.plugins:
                modname = name if "." in name else f"pyprland.plugins.{name}"
                try:
                    plug = importlib.import_module(modname).Extension(name)
                    if init:
                        await plug.init()
                    self.plugins[name] = plug
                except Exception as e:
                    print(f"Error loading plugin {name}: {e}")
                    if DEBUG:
                        traceback.print_exc()
            if init:
                await self.plugins[name].load_config(self.config)

    async def _callHandler(self, full_name, *params):
        for plugin in [self] + list(self.plugins.values()):
            if hasattr(plugin, full_name):
                try:
                    await getattr(plugin, full_name)(*params)
                except Exception as e:
                    print(f"{plugin.name}::{full_name}({params}) failed:")
                    traceback.print_exc()

    async def read_events_loop(self):
        while not self.stopped:
            data = (await self.event_reader.readline()).decode()
            if not data:
                print("Reader starved")
                return
            cmd, params = data.split(">>")
            full_name = f"event_{cmd}"

            if DEBUG:
                print(f"EVT {full_name}({params.strip()})")
            await self._callHandler(full_name, params)

    async def read_command(self, reader, writer) -> None:
        data = (await reader.readline()).decode()
        if not data:
            print("Server starved")
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

        if DEBUG:
            print(f"CMD: {full_name}({args})")

        await self._callHandler(full_name, *args)

    async def serve(self):
        try:
            async with self.server:
                await self.server.serve_forever()
        finally:
            await asyncio.gather(*(plugin.exit() for plugin in self.plugins.values()))

    async def run(self):
        await asyncio.gather(
            asyncio.create_task(self.serve()),
            asyncio.create_task(self.read_events_loop()),
        )

    run_reload = load_config


async def run_daemon():
    manager = Pyprland()
    err_count = itertools.count()
    manager.server = await asyncio.start_unix_server(manager.read_command, CONTROL)
    try:
        events_reader, events_writer = await get_event_stream()
    except Exception as e:
        print("Failed to get event stream: %s" % e)
        if next(err_count) > 10:
            raise
        await asyncio.sleep(1)

    manager.event_reader = events_reader

    try:
        await manager.load_config()  # ensure sockets are connected first
    except FileNotFoundError:
        print(
            f"No config file found, create one at {CONFIG_FILE} with a valid pyprland.plugins list"
        )
        raise SystemExit(1)

    try:
        await manager.run()
    except KeyboardInterrupt:
        print("Interrupted")
    except asyncio.CancelledError:
        print("Bye!")
    finally:
        events_writer.close()
        await events_writer.wait_closed()
        manager.server.close()
        await manager.server.wait_closed()


async def run_client():
    if sys.argv[1] in ("--help", "-h"):
        manager = Pyprland()
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

    _, writer = await asyncio.open_unix_connection(CONTROL)
    writer.write((" ".join(sys.argv[1:])).encode())
    await writer.drain()
    writer.close()
    await writer.wait_closed()


def main():
    try:
        asyncio.run(run_daemon() if len(sys.argv) <= 1 else run_client())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
