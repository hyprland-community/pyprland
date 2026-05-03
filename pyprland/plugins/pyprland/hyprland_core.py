"""Hyprland-specific state management."""

import json
import os
from pathlib import Path
from typing import Any

from ...models import PyprError, VersionInfo
from ..mixins import StateMonitorTrackingMixin

DEFAULT_VERSION = VersionInfo(9, 9, 9)


class HyprlandStateMixin(StateMonitorTrackingMixin):
    """Mixin providing Hyprland-specific state management.

    This mixin is designed to be used with the Extension class and provides
    all Hyprland-specific initialization and event handling.
    """

    # These attributes are provided by the Extension class
    backend: Any
    log: Any
    state: Any
    notify_error: Any

    async def _init_hyprland(self) -> None:
        """Initialize Hyprland-specific state."""
        try:
            version_data = await self.backend.execute_json("version")
            assert isinstance(version_data, dict)
            self.state.hyprland_version = VersionInfo.from_hyprctl(version_data)
        except (FileNotFoundError, json.JSONDecodeError, PyprError, ValueError, IndexError, AssertionError) as e:
            self.log.warning("Fail to parse version information: %s - using default", e)
            self.state.hyprland_version = DEFAULT_VERSION

        # Detect Lua config mode by checking for hyprland.lua file
        config_home = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
        lua_config = Path(config_home) / "hypr" / "hyprland.lua"
        self.state.lua_mode = lua_config.is_file()
        if self.state.lua_mode:
            self.log.info("Lua config detected at %s", lua_config)

        try:
            self.state.active_workspace = (await self.backend.execute_json("activeworkspace"))["name"]
            monitors = await self.backend.get_monitors(include_disabled=True)
            self.state.monitors = [mon["name"] for mon in monitors]
            self.state.set_disabled_monitors({mon["name"] for mon in monitors if mon.get("disabled", False)})
            self.state.active_monitor = next((mon["name"] for mon in monitors if mon["focused"]), "unknown")
        except (FileNotFoundError, PyprError):
            self.log.warning("Hyprland socket not found, assuming no hyprland")
            self.state.active_workspace = "unknown"
            self.state.monitors = []
            self.state.set_disabled_monitors(set())
            self.state.active_monitor = "unknown"

    async def event_configreloaded(self, _: str = "") -> None:
        """Reconcile monitor state after config reload.

        Re-fetches all monitors to update the disabled monitors set,
        since monitor enable/disable happens via config changes.
        """
        try:
            monitors = await self.backend.get_monitors(include_disabled=True)
            self.state.monitors = [mon["name"] for mon in monitors]
            self.state.set_disabled_monitors({mon["name"] for mon in monitors if mon.get("disabled", False)})
        except (FileNotFoundError, PyprError):
            self.log.warning("Failed to reconcile monitors after config reload")

    async def event_activewindowv2(self, addr: str) -> None:
        """Keep track of the focused client.

        Args:
            addr: The window address
        """
        if not addr:
            self.log.debug("no active window")
            self.state.active_window = ""
        else:
            self.state.active_window = "0x" + addr
            self.log.debug("active_window = %s", self.state.active_window)

    async def event_workspace(self, workspace: str) -> None:
        """Track the active workspace.

        Args:
            workspace: The workspace name
        """
        self.state.active_workspace = workspace
        self.log.debug("active_workspace = %s", self.state.active_workspace)

    async def event_focusedmon(self, mon: str) -> None:
        """Track the active monitor.

        Args:
            mon: The monitor description (name,workspace)
        """
        self.state.active_monitor, self.state.active_workspace = mon.rsplit(",", 1)
        self.log.debug("active_monitor = %s", self.state.active_monitor)
