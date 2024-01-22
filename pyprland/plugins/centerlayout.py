" Plugin template "
from typing import Any
from collections import defaultdict

from .interface import Plugin

from ..ipc import hyprctlJSON, hyprctl


class Extension(Plugin):
    "Sample plugin template"

    margin = 100
    workspace_info: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"enabled": False, "addr": ""}
    )
    active_workspace = ""
    active_window_addr = ""

    async def init(self):
        "initializes the plugin"
        for monitor in await hyprctlJSON("monitors"):
            if monitor["focused"]:
                self.active_workspace = str(monitor["activeWorkspace"]["name"])

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
        "<toggle|next|prev> turn on/off or change the active window"
        if what == "toggle":
            await self._run_toggle()
        elif what == "next":
            await self._run_changefocus(1)
        elif what == "prev":
            await self._run_changefocus(-1)

        if self.enabled:
            await hyprctl(f"focuswindow address:{self.addr}")

    # Utils

    async def get_clients(self):
        "Return the client list in the currently active workspace"
        clients = []
        for client in await hyprctlJSON("clients"):
            if client["workspace"]["name"] == self.active_workspace:
                clients.append(client)
        clients.sort(key=lambda c: c["address"])
        return clients

    async def unprepare_window(self):
        "Set the window as normal"
        await hyprctl(f"togglefloating address:{self.addr}")

    async def prepare_window(self):
        "Set the window as centered"
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
        await hyprctl(f"resizewindowpixel exact {width} {height},address:{addr}")
        # await hyprctl(f"centerwindow")
        await hyprctl(f"movewindowpixel exact {x} {y},address:{addr}")

    # Subcommands

    async def _run_changefocus(self, direction):
        "Change the focus in the given direction (>0 or <0)"
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
            await hyprctl(f"movefocus {'r' if direction > 0 else 'l'}")

    async def _run_toggle(self):
        "toggle the center layout"
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
        "Is center layout enabled on the active workspace ?"
        return self.workspace_info[self.active_workspace]["enabled"]

    def set_enabled(self, value):
        "set if center layout enabled on the active workspace"
        self.workspace_info[self.active_workspace]["enabled"] = value

    enabled = property(
        get_enabled, set_enabled, "centered layout enabled on this workspace"
    )
    del get_enabled, set_enabled

    def get_addr(self):
        "get active workspace's centered window address"
        return self.workspace_info[self.active_workspace]["addr"]

    def set_addr(self, value):
        "set active workspace's centered window address"
        self.workspace_info[self.active_workspace]["addr"] = value

    addr = property(
        get_addr, set_addr, doc="active workspace's centered window address"
    )
    del get_addr, set_addr
