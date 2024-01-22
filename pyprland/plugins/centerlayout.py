" Plugin template "
import asyncio
from typing import Any
from collections import defaultdict

from .interface import Plugin

from ..ipc import hyprctlJSON, hyprctl


class Extension(Plugin):
    "Sample plugin template"

    margin = 100

    async def init(self):
        self.workspace_info: dict[str, dict[str, Any]] = defaultdict(
            lambda: dict(enabled=False, addr="")
        )
        self.active_workspace = ""
        for monitor in await hyprctlJSON("monitors"):
            if monitor["focused"]:
                self.active_workspace = str(monitor["activeWorkspace"]["name"])
        # TODO: fetch active client in active_workspace
        self.active_window_addr = ""

    async def event_workspace(self, wrkspace):
        "active workspace hook"
        self.active_workspace = wrkspace.strip()

    async def event_focusedmon(self, mon):
        "focused monitor hook"
        _, self.active_workspace = mon.strip().rsplit(",", 1)

    async def event_activewindowv2(self, addr):
        "focused client hook"
        self.active_window_addr = "0x" + addr.strip()

    async def run_centerlayout(self, what):
        if what == "toggle":
            await self._run_toggle()
        elif what == "next":
            await self._run_changefocus(1)
        elif what == "prev":
            await self._run_changefocus(-1)

    # Utils

    async def get_clients(self):
        clients = []
        for client in await hyprctlJSON("clients"):
            if client["workspace"]["name"] == self.active_workspace:
                clients.append(client)
        clients.sort(key=lambda c: c["address"])
        return clients

    async def unprepare_window(self):
        await hyprctl(f"togglefloating address:{self.addr}")

    async def prepare_window(self):
        addr = self.addr
        await hyprctl(f"togglefloating address:{addr}")
        width = 100
        height = 100
        x = 0
        y = 0
        for monitor in await hyprctlJSON("monitors"):
            if monitor["focused"]:
                width = monitor["width"] - (2 * self.margin)
                height = monitor["height"] - (2 * self.margin)
                x = monitor["x"] + self.margin
                y = monitor["y"] + self.margin
        # await asyncio.sleep(0.2)
        await hyprctl(f"resizewindowpixel exact {width} {height},address:{addr}")
        # await asyncio.sleep(0.2)
        # await hyprctl(f"centerwindow")
        await hyprctl(f"movewindowpixel exact {x} {y},address:{addr}")

    # Subcommands

    async def _run_changefocus(self, direction):
        if self.enabled:
            clients = await self.get_clients()
            index = 0
            for i, client in enumerate(clients):
                if client["address"] == self.addr:
                    index = i + direction
            if index < 0:
                index = len(clients) - 1
            elif index == len(clients):
                index = 0
            new_client = clients[index]
            await self.unprepare_window()
            self.addr = new_client["address"]
            await self.prepare_window()
        else:
            await hyprctl("movefocus %s" % "r" if direction > 0 else "l")

    async def _run_toggle(self):
        disabled = not self.enabled
        if disabled:
            self.addr = self.active_window_addr
            await self.prepare_window()
        else:
            await self.unprepare_window()
            self.addr = None

        self.enabled = not self.enabled

    # Getters

    def get_enabled(self):
        return self.workspace_info[self.active_workspace]["enabled"]

    def set_enabled(self, value):
        self.workspace_info[self.active_workspace]["enabled"] = value

    enabled = property(get_enabled, set_enabled)
    del get_enabled, set_enabled

    def get_addr(self):
        return self.workspace_info[self.active_workspace]["addr"]

    def set_addr(self, value):
        self.workspace_info[self.active_workspace]["addr"] = value

    addr = property(get_addr, set_addr)
    del get_addr, set_addr
