"""stash allows stashing and showing windows in named groups."""

import asyncio
from typing import cast

from ..models import Environment, ReloadReason
from ..validation import ConfigField, ConfigItems
from .interface import Plugin

STASH_PREFIX = "st-"
STASH_TAG = "stashed"


class Extension(Plugin, environments=[Environment.HYPRLAND]):
    """Stash and show windows in named groups using special workspaces."""

    config_schema = ConfigItems(
        ConfigField("style", list, default=[], description="Window rules to apply to shown stash windows", category="basic"),
        ConfigField(
            "restore_floating",
            bool,
            default=True,
            description="Restore original floating/tiled state when showing stash via stash_toggle (set to false for overlay mode)",
            category="basic",
        ),
    )

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self._visible: dict[str, bool] = {}
        self._shown_addresses: dict[str, list[str]] = {}
        self._was_floating: dict[str, bool] = {}

    async def on_reload(self, reason: ReloadReason = ReloadReason.RELOAD) -> None:  # noqa: ARG002
        """Clear old tag rules and re-register window rules for stash styling."""
        await self.backend.execute(
            f"windowrule tag -{STASH_TAG}",
            base_command="keyword",
        )
        style = self.get_config_list("style")
        if style:
            commands = [f"windowrule {rule}, match:tag {STASH_TAG}" for rule in style]
            await self.backend.execute(commands, base_command="keyword")

    async def run_stash(self, name: str = "default") -> None:
        """[name] Toggle stashing the focused window (default stash: "default").

        Args:
            name: The stash group name
        """
        aw = cast("dict", await self.backend.execute_json("activewindow"))
        addr = aw.get("address", "")
        if not addr:
            return

        # If the window was shown via stash_toggle, just remove it from tracking
        restore = self.get_config_bool("restore_floating")
        for group, addresses in self._shown_addresses.items():
            if addr in addresses:
                addresses.remove(addr)
                await self._restore_floating(addr, already_restored=restore)
                if not addresses:
                    self._shown_addresses.pop(group)
                    self._visible[group] = False
                return

        ws_name = aw["workspace"]["name"]
        await asyncio.sleep(0.1)

        if ws_name.startswith(f"special:{STASH_PREFIX}"):
            # Window is stashed → unstash it to current workspace
            await self.backend.move_window_to_workspace(addr, self.state.active_workspace, silent=True)
            await self.backend.focus_window(addr)

            await asyncio.sleep(0.1)
            await self._restore_floating(addr)
        else:
            # Window is not stashed → stash it
            was_floating = aw.get("floating", False)
            self._was_floating[addr] = was_floating
            await self.backend.move_window_to_workspace(addr, f"special:{STASH_PREFIX}{name}", silent=True)
            await asyncio.sleep(0.1)
            if not was_floating:
                await self.backend.toggle_floating(addr)
            await asyncio.sleep(0.1)
            if self.get_config_list("style"):
                await self.backend.execute(f"tagwindow +{STASH_TAG} address:{addr}")

    async def _restore_floating(self, addr: str, *, already_restored: bool = False) -> None:
        """Restore a window's original floating state and remove stash tag.

        Args:
            addr: Window address
            already_restored: If True, floating state was already restored
                (e.g. by _show_stash with restore_floating=True) — skip toggle.
        """
        if not already_restored and not self._was_floating.pop(addr, True):
            await self.backend.toggle_floating(addr)
            await asyncio.sleep(0.1)
        else:
            self._was_floating.pop(addr, None)
        if self.get_config_list("style"):
            await self.backend.execute(f"tagwindow -{STASH_TAG} address:{addr}")

    async def event_closewindow(self, addr: str) -> None:
        """Remove a closed window from stash tracking.

        Args:
            addr: Window address as hex string (without 0x prefix)
        """
        addr = "0x" + addr
        self._was_floating.pop(addr, None)
        for group in list(self._shown_addresses):
            addresses = self._shown_addresses[group]
            if addr in addresses:
                addresses.remove(addr)
                if not addresses:
                    del self._shown_addresses[group]
                    self._visible[group] = False

    async def run_stash_toggle(self, name: str = "default") -> None:
        """[name] Show or hide stash "name" on the active workspace (default: "default").

        When showing, windows are moved from the hidden stash workspace to the
        active workspace.  When ``restore_floating`` is enabled (the default),
        originally-tiled windows are restored to tiled; otherwise they remain
        floating (overlay mode).  When hiding, they are moved back.

        Args:
            name: The stash group name
        """
        if self._visible.get(name, False):
            await self._hide_stash(name)
        else:
            await self._show_stash(name)

    async def _show_stash(self, name: str) -> None:
        """Move stashed windows to the active workspace."""
        stash_ws = f"special:{STASH_PREFIX}{name}"
        clients = await self.get_clients(workspace=stash_ws)
        if not clients:
            return

        restore = self.get_config_bool("restore_floating")
        addresses: list[str] = []
        for client in clients:
            addr = client["address"]
            addresses.append(addr)
            await self.backend.move_window_to_workspace(addr, self.state.active_workspace, silent=True)
            if restore and not self._was_floating.get(addr, True):
                await asyncio.sleep(0.1)
                await self.backend.toggle_floating(addr)

        self._shown_addresses[name] = addresses
        self._visible[name] = True

    async def _hide_stash(self, name: str) -> None:
        """Move previously shown stash windows back to the hidden workspace."""
        stash_ws = f"special:{STASH_PREFIX}{name}"
        addresses = self._shown_addresses.get(name, [])
        restore = self.get_config_bool("restore_floating")

        for addr in addresses:
            if restore and not self._was_floating.get(addr, True):
                # Window was restored to tiled by _show_stash; re-float before
                # moving back to the special workspace.
                await self.backend.toggle_floating(addr)
                await asyncio.sleep(0.1)
            await self.backend.move_window_to_workspace(addr, stash_ws)

        self._shown_addresses.pop(name, None)
        self._visible[name] = False
