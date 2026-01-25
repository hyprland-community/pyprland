"""Core plugin for state management.

This plugin is not a real plugin - it provides core features and caching
of commonly requested structures. It handles initialization and state
tracking for both Hyprland and Niri environments.
"""

from ...models import VersionInfo
from ..interface import Plugin
from .hyprland_core import HyprlandStateMixin
from .niri_core import NiriStateMixin
from .schema import PYPRLAND_CONFIG_SCHEMA

DEFAULT_VERSION = VersionInfo(9, 9, 9)


class Extension(HyprlandStateMixin, NiriStateMixin, Plugin):
    """Internal built-in plugin allowing caching states and implementing special commands."""

    config_schema = PYPRLAND_CONFIG_SCHEMA

    async def init(self) -> None:
        """Initialize the plugin."""
        self.state.active_window = ""

        if self.state.environment == "niri":
            await self._init_niri()
        else:
            await self._init_hyprland()

    async def on_reload(self) -> None:
        """Reload the plugin."""
        self.state.variables = self.get_config_dict("variables")
        version_override = self.get_config_str("hyprland_version")
        if version_override:
            self._set_hyprland_version(version_override)

    def set_commands(self, **cmd_map) -> None:
        """Set some commands, made available as run_`name` methods.

        Args:
            cmd_map: The map of commands
        """
        for name, fn in cmd_map.items():
            setattr(self, f"run_{name}", fn)
