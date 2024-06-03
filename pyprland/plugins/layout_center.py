"""Implements a "Centered" layout.

- windows are normally tiled but one
- the active window is floating and centered
- you can cycle the active window, keeping the same layout type
- layout can be toggled any time
"""

from collections import defaultdict
from typing import Any, cast

from ..common import CastBoolMixin, is_rotated, state
from ..types import ClientInfo, MonitorInfo
from .interface import Plugin


class Extension(CastBoolMixin, Plugin):
    """Manages a layout with one centered window on top of others."""

    workspace_info: dict[str, dict[str, Any]] = defaultdict(lambda: {"enabled": False, "addr": ""})
    last_index = 0

    # Events

    async def event_openwindow(self, windescr: str) -> None:
        """Re-set focus to main if a window is opened."""
        if not self.enabled:
            return
        win_addr = "0x" + windescr.split(",", 1)[0]

        behavior = self.config.get("on_new_client", "focus")
        new_client: ClientInfo | None = None
        clients = await self.get_clients()
        new_client_idx = 0
        for i, cli in enumerate(clients):
            if cli["address"] == win_addr:
                new_client = cli
                new_client_idx = i
                break

        if new_client:
            self.last_index = new_client_idx
            if behavior == "background" and not new_client["floating"]:
                # focus back to main client unless it's a floating window
                await self.hyprctl(f"focuswindow address:{self.main_window_addr}")
            elif behavior == "foreground":
                # make the new client the main window
                await self.unprepare_window(clients)
                self.main_window_addr = win_addr
                await self.prepare_window(clients)
            else:  # close
                await self._run_toggle()

    async def event_activewindowv2(self, _: str) -> None:
        """Keep track of focused client."""
        captive = self.cast_bool(self.config.get("captive_focus"))
        is_not_active = state.active_window != self.main_window_addr
        if captive and self.enabled and is_not_active:
            try:
                next(c for c in await self.get_clients() if c["address"] == state.active_window)
            except StopIteration:
                pass
            else:
                await self.hyprctl(f"focuswindow address:{self.main_window_addr}")

    async def event_closewindow(self, addr: str) -> None:
        """Disable when the main window is closed."""
        addr = "0x" + addr
        clients = [c for c in await self.get_clients() if c["address"] != addr]
        if self.enabled and await self._sanity_check(clients):
            closed_main = self.main_window_addr == addr
            if self.enabled and closed_main:
                self.log.debug("main window closed, focusing next")
                await self._run_changefocus(1)

    # Command

    async def run_layout_center(self, what: str) -> None:
        """<toggle|next|prev> turn on/off or change the active window."""
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

    async def on_reload(self) -> None:
        """Loads the configuration and apply the tag style."""
        if not self.config.get("style"):
            return
        await self.hyprctl("windowrulev2 unset, tag:layout_center")
        commands = [f"windowrulev2 {rule}, tag:layout_center" for rule in self.config.get("style", [])]
        if commands:
            await self.hyprctl(commands)

    # Utils

    async def get_clients(self, *_) -> list[ClientInfo]:  # pylint: disable=arguments-differ
        """Return the client list in the currently active workspace."""
        clients = await super().get_clients(mapped=True, workspace=state.active_workspace)
        clients.sort(key=lambda c: c["address"])
        return clients

    async def unprepare_window(self, clients: list[ClientInfo] | None = None) -> None:
        """Set the window as normal."""
        if not clients:
            clients = await self.get_clients()
        addr = self.main_window_addr
        for cli in clients:
            if cli["address"] == addr and cli["floating"]:
                await self.hyprctl(f"togglefloating address:{addr}")
                if self.config.get("style"):
                    await self.hyprctl(f"tagwindow -layout_center address:{addr}")
                break

    async def prepare_window(self, clients: list[ClientInfo] | None = None) -> None:
        """Set the window as centered."""
        if not clients:
            clients = await self.get_clients()
        addr = self.main_window_addr
        for cli in clients:
            if cli["address"] == addr and not cli["floating"]:
                await self.hyprctl(f"togglefloating address:{addr}")
                if self.config.get("style"):
                    await self.hyprctl(f"tagwindow +layout_center address:{addr}")
                break
        width = 100
        height = 100
        x, y = self.offset
        m = self.margin
        margin: tuple[int, int] = (m, m) if isinstance(m, int) else m
        scale = 1
        for monitor in cast(list[dict[str, Any]], await self.hyprctl_json("monitors")):
            scale = monitor["scale"]
            if monitor["focused"]:
                width = monitor["width"] - (2 * margin[0])
                height = monitor["height"] - (2 * margin[1])
                if is_rotated(cast(MonitorInfo, monitor)):
                    width, height = height, width
                x += monitor["x"] + margin[0]
                y += monitor["y"] + margin[1]
                break
        await self.hyprctl(f"resizewindowpixel exact {int(width / scale)} {int(height / scale)},address:{addr}")
        await self.hyprctl(f"movewindowpixel exact {int(x / scale)} {int(y / scale)},address:{addr}")

    # Subcommands

    async def _sanity_check(self, clients: list[ClientInfo] | None = None) -> bool:
        """Auto-disable if needed & return enabled status."""
        clients = clients or await self.get_clients()
        if len(clients) < 2:  # noqa: PLR2004
            # If < 2 clients, disable the layout & stop
            self.log.info("disabling (clients starvation)")
            await self.unprepare_window()
            self.enabled = False
        return self.enabled

    async def _run_changefocus(self, direction: int, default_override: str | None = None) -> None:
        """Change the focus in the given direction (-1 or 1)."""
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
        elif default_override:
            command = self.config.get(default_override)
            if command:
                await self.hyprctl(command)

    async def _run_toggle(self) -> None:
        """Toggle the center layout."""
        disabled = not self.enabled
        if disabled:
            self.main_window_addr = state.active_window
            await self.prepare_window()
        else:
            await self.unprepare_window()

        self.enabled = disabled

    # Properties

    @property
    def offset(self) -> tuple[int, int]:
        """Returns the centered window offset."""
        offset = self.config.get("offset", (0, 0))
        if isinstance(offset, str):
            x, y = (int(i) for i in self.config["offset"].split() if i.strip())
            return (x, y)
        return cast(tuple[int, int], offset)

    @property
    def margin(self) -> int:
        """Returns the margin of the centered window."""
        return cast(int, self.config.get("margin", 60))

    # enabled
    @property
    def enabled(self) -> bool:
        """Is center layout enabled on the active workspace ?."""
        return cast(bool, self.workspace_info[state.active_workspace]["enabled"])

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set if center layout enabled on the active workspace."""
        self.workspace_info[state.active_workspace]["enabled"] = value

    # main_window_addr

    @property
    def main_window_addr(self) -> str:
        """Get active workspace's centered window address."""
        return cast(str, self.workspace_info[state.active_workspace]["addr"])

    @main_window_addr.setter
    def main_window_addr(self, value: str) -> None:
        """Set active workspace's centered window address."""
        self.workspace_info[state.active_workspace]["addr"] = value
