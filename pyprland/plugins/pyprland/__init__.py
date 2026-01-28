"""Core plugin for state management.

This plugin is not a real plugin - it provides core features and caching
of commonly requested structures. It handles initialization and state
tracking for both Hyprland and Niri environments.
"""

import json
from typing import TYPE_CHECKING

from ...completions import handle_compgen
from ...help import get_command_help, get_help
from ...models import VersionInfo
from ...version import VERSION
from ..interface import Plugin
from .hyprland_core import HyprlandStateMixin
from .niri_core import NiriStateMixin
from .schema import PYPRLAND_CONFIG_SCHEMA

if TYPE_CHECKING:
    from ...manager import Pyprland

DEFAULT_VERSION = VersionInfo(9, 9, 9)


class Extension(HyprlandStateMixin, NiriStateMixin, Plugin):
    """Internal built-in plugin allowing caching states and implementing special commands."""

    config_schema = PYPRLAND_CONFIG_SCHEMA
    manager: "Pyprland"  # Set by manager during init

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

    def run_version(self) -> str:
        """Show the pyprland version."""
        return f"{VERSION}\n"

    def run_dumpjson(self) -> str:
        """Dump the configuration in JSON format (after includes are processed)."""
        return json.dumps(self.manager.config, indent=2)

    def run_help(self, command: str = "") -> str:
        """[command] Show available commands or detailed help.

        Usage:
          pypr help           List all commands
          pypr help <command> Show detailed help
        """
        return get_command_help(self.manager, command) if command else get_help(self.manager)

    async def run_reload(self) -> None:
        """Reload the configuration file.

        New plugins will be loaded and configuration options will be updated.
        Most plugins will use the new values on the next command invocation.
        """
        await self.manager.load_config()

    def run_compgen(self, args: str = "") -> str:
        """<shell> [default|path] Generate shell completions.

        Usage:
          pypr compgen <shell>            Output script to stdout
          pypr compgen <shell> default    Install to default user path
          pypr compgen <shell> ~/path     Install to home-relative path
          pypr compgen <shell> /abs/path  Install to absolute path

        Examples:
          pypr compgen zsh > ~/.zsh/completions/_pypr
          pypr compgen bash default
        """
        success, result = handle_compgen(self.manager, args)
        if not success:
            raise ValueError(result)
        return result

    def run_exit(self) -> None:
        """Terminate the pyprland daemon."""
        self.manager.stopped = True
