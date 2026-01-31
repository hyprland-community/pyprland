"""Shared state management for cross-plugin coordination.

SharedState is a dataclass holding commonly-accessed mutable state:
- Active workspace, monitor, and window
- Environment type (hyprland, niri, wayland, xorg)
- Monitor list with disabled monitor tracking
- Hyprland version info

Passed to all plugins via plugin.state for coordination.
"""

from dataclasses import dataclass, field

from .models import VersionInfo

__all__ = [
    "SharedState",
]


@dataclass
class SharedState:
    """Stores commonly requested properties."""

    active_workspace: str = ""  # workspace name
    active_monitor: str = ""  # monitor name
    active_window: str = ""  # window address
    environment: str = "hyprland"
    variables: dict = field(default_factory=dict)
    monitors: list[str] = field(default_factory=list)  # ALL monitors (source of truth)
    _disabled_monitors: set[str] = field(default_factory=set)  # Disabled monitor names
    hyprland_version: VersionInfo = field(default_factory=VersionInfo)

    @property
    def active_monitors(self) -> list[str]:
        """Return only active/enabled monitors."""
        return [m for m in self.monitors if m not in self._disabled_monitors]

    def set_disabled_monitors(self, disabled: set[str]) -> None:
        """Update the set of disabled monitors.

        Args:
            disabled: Set of monitor names that are disabled.
        """
        self._disabled_monitors = disabled
