"""Niri-specific state management."""

from typing import Any

from ...models import Environment, PyprError, VersionInfo

DEFAULT_VERSION = VersionInfo(9, 9, 9)


class NiriStateMixin:
    """Mixin providing Niri-specific state management.

    This mixin is designed to be used with the Extension class and provides
    all Niri-specific initialization and event handling.
    """

    # These attributes are provided by the Extension class
    backend: Any
    log: Any
    state: Any

    async def _init_niri(self) -> None:
        """Initialize Niri-specific state."""
        try:
            self.state.active_workspace = "unknown"  # Niri workspaces are dynamic/different
            outputs = await self.backend.execute_json("outputs")
            self.state.monitors = list(outputs.keys())
            # Disabled outputs have current_mode set to None
            self.state.set_disabled_monitors({name for name, data in outputs.items() if data.get("current_mode") is None})
            self.state.active_monitor = next(
                (name for name, data in outputs.items() if data.get("is_focused")),
                "unknown",
            )
            # Set a dummy version for Niri since we don't have version info yet
            self.state.hyprland_version = DEFAULT_VERSION
        except (FileNotFoundError, PyprError):
            self.log.warning("Niri socket not found or failed to query")
            self.state.active_workspace = "unknown"
            self.state.monitors = []
            self.state.set_disabled_monitors(set())
            self.state.active_monitor = "unknown"

    async def niri_outputschanged(self, _data: dict) -> None:
        """Track monitors on Niri.

        Args:
            _data: The event data (unused)
        """
        if self.state.environment == Environment.NIRI:
            try:
                outputs = await self.backend.execute_json("outputs")
                self.state.monitors = list(outputs.keys())
                # Disabled outputs have current_mode set to None
                self.state.set_disabled_monitors({name for name, data in outputs.items() if data.get("current_mode") is None})
                self.state.active_monitor = next(
                    (name for name, data in outputs.items() if data.get("is_focused")),
                    "unknown",
                )
            except (OSError, RuntimeError) as e:
                self.log.warning("Failed to update monitors from Niri event: %s", e)
