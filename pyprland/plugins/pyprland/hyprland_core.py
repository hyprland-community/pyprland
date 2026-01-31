"""Hyprland-specific state management."""

import json
from typing import Any, cast

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
        # Examples:
        # "tag": "v0.40.0-127-g4e42107d", (for git)
        # "tag": "v0.40.0", (stable)
        version_str = ""
        auto_increment = False
        version_info = {}
        try:
            version_info = await self.backend.execute_json("version")
            assert isinstance(version_info, dict)
        except (FileNotFoundError, json.JSONDecodeError, PyprError):
            self.log.warning("Fail to parse hyprctl version")
        else:
            _tag = version_info.get("tag")

            if _tag and _tag != "unknown":
                assert isinstance(_tag, str)
                version_str = _tag.split("-", 1)[0]
                if len(version_str) < len(_tag):
                    auto_increment = True
            else:
                version_str = cast("str", version_info.get("version"))

        if version_str:
            try:
                self._set_hyprland_version(
                    version_str.removeprefix("v"),
                    auto_increment,
                )
            except (ValueError, IndexError):
                self.log.exception('Fail to parse version tag "%s"', version_str)
                await self.backend.notify_error(f"Failed to parse hyprctl version tag: {version_str}")
                version_str = ""

        if not version_str:
            self.log.warning("Fail to parse version information: %s - using default", version_info)
            self.state.hyprland_version = DEFAULT_VERSION

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

    def _set_hyprland_version(self, version_str: str, auto_increment: bool = False) -> None:
        """Set the hyprland version.

        Args:
            version_str: The version string
            auto_increment: Whether to auto-increment the version
        """
        split_version = [int(i) for i in version_str.split(".")[:3]]
        if auto_increment:
            split_version[-1] += 1
        self.state.hyprland_version = VersionInfo(*split_version)
