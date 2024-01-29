"""
Implements a "Centered" layout:
- windows are normally tiled but one
- the active window is floating and centered
- you can cycle the active window, keeping the same layout type
- layout can be toggled any time
"""
from typing import Any, cast
from collections import defaultdict

from .interface import Plugin

from ..ipc import hyprctlJSON, hyprctl


class Extension(Plugin):
    "Manages a layout with one centered window on top of others"

    workspace_info: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"enabled": False, "addr": ""}
    )
    active_workspace = ""
    # focused window
    active_window_addr = ""
    # main centered window
    main_window_addr = ""

    async def init(self):
        "initializes the plugin"
        for monitor in await hyprctlJSON("monitors"):
            assert isinstance(monitor, dict)
            if monitor["focused"]:
                self.active_workspace = cast(str, monitor["activeWorkspace"]["name"])

    # Events

    async def event_workspace(self, wrkspace):
        "track the active workspace"
        self.active_workspace = wrkspace

    async def event_focusedmon(self, mon):
        "track the active workspace"
        _, self.active_workspace = mon.rsplit(",", 1)

    async def event_activewindowv2(self, addr):
        "keep track of focused client"
        self.active_window_addr = "0x" + addr

    async def event_closewindow(self, addr):
        "Disable when the main window is closed"
        closed_main = self.main_window_addr == "0x" + addr
        if self.enabled and closed_main:
            await self._run_toggle()

    # Command

    async def run_centerlayout(self, what):
        "<toggle|next|prev> turn on/off or change the active window"
        if what == "toggle":
            await self._run_toggle()
        elif what == "next":
            await self._run_changefocus(1)
        elif what == "prev":
            await self._run_changefocus(-1)

        if self.enabled:
            await hyprctl(f"focuswindow address:{self.main_window_addr}")

    # Utils

    async def get_clients(self):
        "Return the client list in the currently active workspace"
        clients = [
            client
            for client in cast(list[dict[str, Any]], await hyprctlJSON("clients"))
            if cast(str, client["workspace"]["name"]) == self.active_workspace
        ]
        clients.sort(key=lambda c: c["address"])
        return clients

    async def unprepare_window(self, clients=None):
        "Set the window as normal"
        if not clients:
            clients = await self.get_clients()
        addr = self.main_window_addr
        for cli in clients:
            if cli["address"] == addr and cli["floating"]:
                await hyprctl(f"togglefloating address:{addr}")

    async def prepare_window(self, clients=None):
        "Set the window as centered"
        if not clients:
            clients = await self.get_clients()
        addr = self.main_window_addr
        for cli in clients:
            if cli["address"] == addr and not cli["floating"]:
                await hyprctl(f"togglefloating address:{addr}")
        width = 100
        height = 100
        x = 0
        y = 0
        margin = self.margin
        for monitor in cast(list[dict[str, Any]], await hyprctlJSON("monitors")):
            if monitor["focused"]:
                width = monitor["width"] - (2 * margin)
                height = monitor["height"] - (2 * margin)
                x = monitor["x"] + margin
                y = monitor["y"] + margin
        await hyprctl(f"movewindowpixel exact {x} {y},address:{addr}")
        await hyprctl(f"resizewindowpixel exact {width} {height},address:{addr}")
        # await hyprctl(f"centerwindow")

    # Subcommands

    async def _run_changefocus(self, direction):
        "Change the focus in the given direction (>0 or <0)"
        if self.enabled:
            clients = await self.get_clients()
            if len(clients) < 2:
                # If < 2 clients, disable the layout & stop
                await self.unprepare_window()
                return
            index = 0
            for i, client in enumerate(clients):
                if client["address"] == self.main_window_addr:
                    index = i + direction
                    break
            if index < 0:
                index = len(clients) - 1
            elif index == len(clients):
                index = 0
            new_client = clients[index]
            self.main_window_addr = new_client["address"]
            await self.unprepare_window(clients)
            await self.prepare_window(clients)
        else:
            orientation = "ud" if self.config.get("vertical") else "lr"
            await hyprctl(f"movefocus {orientation[1 if direction > 0 else 0]}")

    async def _run_toggle(self):
        "toggle the center layout"
        disabled = not self.enabled
        if disabled:
            self.main_window_addr = self.active_window_addr
            await self.prepare_window()
        else:
            await self.unprepare_window()

        self.enabled = disabled

    # Getters

    @property
    def margin(self):
        "Returns the margin of the centered window"
        return self.config.get("margin", 100)

    def get_enabled(self):
        "Is center layout enabled on the active workspace ?"
        return self.workspace_info[self.active_workspace]["enabled"]

    def set_enabled(self, value):
        "set if center layout enabled on the active workspace"
        self.workspace_info[self.active_workspace]["enabled"] = value

    enabled = property(
        get_enabled, set_enabled, doc="centered layout enabled on this workspace"
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
