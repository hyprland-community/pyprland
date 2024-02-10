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
from ..common import state


class Extension(Plugin):
    "Manages a layout with one centered window on top of others"

    workspace_info: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"enabled": False, "addr": ""}
    )
    last_index = 0

    # Events

    async def event_openwindow(self, windescr):
        "Re-set focus to main if a window is opened"
        if not self.enabled:
            return
        win_addr = "0x" + windescr.split(",", 1)[0]
        for i, cli in enumerate(await self.get_clients()):
            if cli["address"] == win_addr and not cli["floating"]:
                await self.hyprctl(f"focuswindow address:{self.main_window_addr}")
                self.last_index = i
                break

    async def event_activewindowv2(self, _):
        "keep track of focused client"
        if (
            self.config.get("captive_focus")
            and self.enabled
            and state.active_window != self.main_window_addr
            and len(
                [
                    c
                    for c in await self.get_clients()
                    if c["address"] == state.active_window
                ]
            )
            > 0
        ):
            await self.hyprctl(f"focuswindow address:{self.main_window_addr}")

    async def event_closewindow(self, addr):
        "Disable when the main window is closed"
        addr = "0x" + addr
        clients = [c for c in await self.get_clients() if c["address"] != addr]
        if self.enabled and await self._sanity_check(clients):
            closed_main = self.main_window_addr == addr
            if self.enabled and closed_main:
                self.log.debug("main window closed, focusing next")
                await self._run_changefocus(1)

    # Command

    async def run_layout_center(self, what):
        "<toggle|next|prev> turn on/off or change the active window"
        if what == "toggle":
            await self._run_toggle()
        elif what == "next":
            await self._run_changefocus(1, default_override="next")
        elif what == "prev":
            await self._run_changefocus(-1, default_override="prev")
        elif what == "next2":
            await self._run_changefocus(1, default_override="next2")
        elif what == "prev2":
            await self._run_changefocus(-1, default_override="prev2")
        else:
            await self.notify_error(f"unknown layout_center command: {what}")

    # Utils

    async def get_clients(self):  # pylint: disable=arguments-differ
        "Return the client list in the currently active workspace"
        clients = await super().get_clients(
            mapped=True, workspace=state.active_workspace
        )
        clients.sort(key=lambda c: c["address"])
        return clients

    async def unprepare_window(self, clients=None):
        "Set the window as normal"
        if not clients:
            clients = await self.get_clients()
        addr = self.main_window_addr
        for cli in clients:
            if cli["address"] == addr and cli["floating"]:
                await self.hyprctl(f"togglefloating address:{addr}")

    async def prepare_window(self, clients=None):
        "Set the window as centered"
        if not clients:
            clients = await self.get_clients()
        addr = self.main_window_addr
        for cli in clients:
            if cli["address"] == addr and not cli["floating"]:
                await self.hyprctl(f"togglefloating address:{addr}")
        width = 100
        height = 100
        x, y = self.offset
        margin = self.margin
        for monitor in cast(list[dict[str, Any]], await self.hyprctlJSON("monitors")):
            if monitor["focused"]:
                width = monitor["width"] - (2 * margin)
                height = monitor["height"] - (2 * margin)
                x += monitor["x"] + margin
                y += monitor["y"] + margin
                break
        await self.hyprctl(f"resizewindowpixel exact {width} {height},address:{addr}")
        await self.hyprctl(f"movewindowpixel exact {x} {y},address:{addr}")

    # Subcommands

    async def _sanity_check(self, clients=None):
        "Auto-disable if needed & return enabled status"
        clients = clients or await self.get_clients()
        if len(clients) < 2:
            # If < 2 clients, disable the layout & stop
            self.log.info("disabling (clients starvation)")
            await self.unprepare_window()
            self.enabled = False
        return self.enabled

    async def _run_changefocus(self, direction, default_override=None):
        "Change the focus in the given direction (-1 or 1)"
        if self.enabled:
            clients = await self.get_clients()
            if await self._sanity_check(clients):
                addresses = [c["address"] for c in clients]
                try:
                    idx = addresses.index(self.main_window_addr)
                except ValueError:
                    idx = self.last_index
                index = idx + direction
                if index < 0:
                    index = len(clients) - 1
                elif index >= len(clients):
                    index = 0
                new_client = clients[index]
                await self.unprepare_window(clients)
                self.main_window_addr = new_client["address"]
                await self.hyprctl(f"focuswindow address:{self.main_window_addr}")
                self.last_index = index
                await self.prepare_window(clients)
        else:
            command = self.config.get(default_override)
            if command:
                await self.hyprctl(command)

    async def _run_toggle(self):
        "toggle the center layout"
        disabled = not self.enabled
        if disabled:
            self.main_window_addr = state.active_window
            await self.prepare_window()
        else:
            await self.unprepare_window()

        self.enabled = disabled

    # Properties

    @property
    def offset(self):
        "Returns the centered window offset"
        offset = self.config.get("offset", [0, 0])
        if isinstance(offset, str):
            x, y = (int(i) for i in self.config["offset"].split() if i.strip())
            return [x, y]
        return offset

    @property
    def margin(self):
        "Returns the margin of the centered window"
        return self.config.get("margin", 60)

    # enabled
    def get_enabled(self):
        "Is center layout enabled on the active workspace ?"
        return self.workspace_info[state.active_workspace]["enabled"]

    def set_enabled(self, value):
        "set if center layout enabled on the active workspace"
        self.workspace_info[state.active_workspace]["enabled"] = value

    enabled = property(
        get_enabled, set_enabled, doc="centered layout enabled on this workspace"
    )
    del get_enabled, set_enabled

    # main_window_addr
    def get_main_window_addr(self):
        "get active workspace's centered window address"
        return self.workspace_info[state.active_workspace]["addr"]

    def set_main_window_addr(self, value):
        "set active workspace's centered window address"
        self.workspace_info[state.active_workspace]["addr"] = value

    main_window_addr = property(
        get_main_window_addr,
        set_main_window_addr,
        doc="active workspace's centered window address",
    )
    del get_main_window_addr, set_main_window_addr
