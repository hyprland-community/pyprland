"""Core plugin for state management.

This plugin is not a real plugin - it provides core features and caching
of commonly requested structures. It handles initialization and state
tracking for both Hyprland and Niri environments.
"""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ...completions import handle_compgen
from ...config import BOOL_FALSE_STRINGS, BOOL_TRUE_STRINGS
from ...help import get_command_help, get_help
from ...models import ReloadReason, VersionInfo
from ...validation import ConfigField, ConfigItems
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

    async def on_reload(self, reason: ReloadReason = ReloadReason.RELOAD) -> None:
        """Reload the plugin."""
        _ = reason  # unused
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

    def _parse_config_path(self, path: str) -> tuple[str, list[str]]:
        """Parse a dot-separated config path into plugin name and keys.

        Args:
            path: Dot-separated config path (e.g., 'wallpapers.online_ratio')

        Returns:
            Tuple of (plugin_name, [key_path_parts])

        Raises:
            ValueError: If path format is invalid
        """
        min_parts = 2
        parts = path.split(".")
        if len(parts) < min_parts:
            msg = f"Invalid path '{path}': use 'plugin.key' format"
            raise ValueError(msg)
        return parts[0], parts[1:]

    def _get_nested_value(self, data: dict, keys: list[str]) -> Any:
        """Get a nested value from a dict using a list of keys.

        Args:
            data: The dictionary to traverse
            keys: List of keys to follow

        Returns:
            The value at the nested path

        Raises:
            KeyError: If any key in the path doesn't exist
        """
        current: Any = data
        for key in keys:
            if not isinstance(current, dict):
                msg = f"Cannot access '{key}' on non-dict value"
                raise KeyError(msg)
            current = current[key]
        return current

    def _set_nested_value(self, data: dict, keys: list[str], value: Any) -> None:
        """Set a nested value in a dict using a list of keys.

        Args:
            data: The dictionary to modify
            keys: List of keys to follow (creates intermediate dicts if needed)
            value: The value to set
        """
        current = data
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def _delete_nested_value(self, data: dict, keys: list[str]) -> bool:
        """Delete a nested value from a dict.

        Args:
            data: The dictionary to modify
            keys: List of keys to follow

        Returns:
            True if deleted, False if key didn't exist
        """
        current = data
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                return False
            current = current[key]
        if keys[-1] in current:
            del current[keys[-1]]
            return True
        return False

    def _get_field_schema(self, plugin_name: str, keys: list[str]) -> ConfigField | None:
        """Get the schema field for a config path.

        Args:
            plugin_name: Name of the plugin
            keys: List of keys within the plugin config

        Returns:
            ConfigField if found, None otherwise
        """
        if plugin_name not in self.manager.plugins:
            return None

        plugin = self.manager.plugins[plugin_name]
        current_schema: ConfigItems | None = getattr(plugin, "config_schema", None)
        if not current_schema:
            return None

        # Navigate through nested schema
        for i, key in enumerate(keys):
            field = current_schema.get(key)
            if not field:
                return None
            if i < len(keys) - 1:
                # Need to go deeper
                if field.children:
                    current_schema = field.children
                else:
                    return None
            else:
                return field
        return None

    def _coerce_value(self, value_str: str, field: ConfigField | None, current_value: Any) -> Any:
        """Coerce a string value to the appropriate type.

        Args:
            value_str: The string value from user input
            field: Schema field if available
            current_value: Current value for type inference fallback

        Returns:
            The coerced value
        """
        # Handle None/unset
        if value_str.lower() == "none":
            return None

        # Determine target type
        target_type = self._get_target_type(field, current_value)

        # Coerce based on type
        if target_type is None:
            return value_str

        return self._coerce_to_type(value_str, target_type)

    def _get_target_type(self, field: ConfigField | None, current_value: Any) -> type | None:
        """Get target type from schema field or current value."""
        if field:
            ft = field.field_type
            return ft[0] if isinstance(ft, tuple) else ft
        if current_value is not None:
            return type(current_value)
        return None

    def _coerce_to_type(self, value_str: str, target_type: type) -> Any:  # noqa: PLR0911
        """Coerce string to specific type."""
        if target_type is bool:
            return self._parse_bool(value_str)

        if target_type is int:
            return int(value_str)

        if target_type is float:
            return float(value_str)

        if target_type is list:
            return self._parse_list(value_str)

        if target_type is dict:
            return json.loads(value_str)

        if target_type is Path or (isinstance(target_type, type) and issubclass(target_type, Path)):
            return value_str  # Paths are stored as strings

        # Default: string
        return value_str

    def _parse_bool(self, value_str: str) -> bool:
        """Parse boolean from string."""
        lower = value_str.lower().strip()
        if lower in BOOL_TRUE_STRINGS:
            return True
        if lower in BOOL_FALSE_STRINGS:
            return False
        msg = f"Invalid boolean: '{value_str}'"
        raise ValueError(msg)

    def _parse_list(self, value_str: str) -> list:
        """Parse list from JSON or comma-separated string."""
        try:
            parsed = json.loads(value_str)
            if isinstance(parsed, list):
                return parsed
        except json.JSONDecodeError:
            pass
        # Comma-separated fallback
        return [item.strip() for item in value_str.split(",")]

    def run_get(self, path: str) -> str:
        """<plugin.key> Get a configuration value.

        Args:
            path: Dot-separated path (e.g., 'wallpapers.online_ratio')

        Examples:
            pypr get wallpapers.online_ratio
            pypr get scratchpads.term.command
        """
        try:
            plugin_name, keys = self._parse_config_path(path)
        except ValueError as e:
            raise ValueError(str(e)) from e

        if plugin_name not in self.manager.config:
            msg = f"Plugin '{plugin_name}' not found in config"
            raise ValueError(msg)

        plugin_config = self.manager.config[plugin_name]

        try:
            value = self._get_nested_value(plugin_config, keys)
        except KeyError:
            # Try schema default
            field = self._get_field_schema(plugin_name, keys)
            if field and field.default is not None:
                value = field.default
            else:
                msg = f"Key '{'.'.join(keys)}' not found in {plugin_name}"
                raise ValueError(msg) from None

        # Format output
        if isinstance(value, (dict, list)):
            return json.dumps(value, indent=2)
        return str(value)

    async def run_set(self, args: str) -> str:  # noqa: C901
        """<plugin.key> <value> Set a configuration value.

        Args:
            args: Path and value (e.g., 'wallpapers.online_ratio 0.5')

        Use 'None' to unset a non-required option.

        Examples:
            pypr set wallpapers.online_ratio 0.5
            pypr set wallpapers.path /new/path
            pypr set scratchpads.term.lazy true
            pypr set wallpapers.online_ratio None
        """
        min_parts = 2
        parts = args.split(None, 1)
        if len(parts) < min_parts:
            msg = "Usage: pypr set <plugin.key> <value>"
            raise ValueError(msg)

        path, value_str = parts

        try:
            plugin_name, keys = self._parse_config_path(path)
        except ValueError as e:
            raise ValueError(str(e)) from e

        if plugin_name not in self.manager.plugins:
            msg = f"Plugin '{plugin_name}' not found"
            raise ValueError(msg)

        # Get schema info
        field = self._get_field_schema(plugin_name, keys)

        # Get current value for type inference
        plugin_config = self.manager.config.get(plugin_name, {})
        try:
            current_value = self._get_nested_value(plugin_config, keys)
        except KeyError:
            current_value = None

        # Coerce value
        try:
            new_value = self._coerce_value(value_str, field, current_value)
        except (ValueError, json.JSONDecodeError) as e:
            msg = f"Invalid value: {e}"
            raise ValueError(msg) from e

        # Handle None (unset)
        if new_value is None:
            if field and field.required:
                msg = f"Cannot unset required field '{'.'.join(keys)}'"
                raise ValueError(msg)
            if plugin_name not in self.manager.config:
                return f"{path} already unset"
            if self._delete_nested_value(self.manager.config[plugin_name], keys):
                # Reload plugin
                plugin = self.manager.plugins[plugin_name]
                await plugin.load_config(self.manager.config)
                await plugin.on_reload()
                return f"{path} unset"
            return f"{path} already unset"

        # Set the value
        if plugin_name not in self.manager.config:
            self.manager.config[plugin_name] = {}
        self._set_nested_value(self.manager.config[plugin_name], keys, new_value)

        # Reload the affected plugin
        plugin = self.manager.plugins[plugin_name]
        await plugin.load_config(self.manager.config)
        await plugin.on_reload()

        # Format response
        if isinstance(new_value, (dict, list)):
            return f"{path} = {json.dumps(new_value)}"
        return f"{path} = {new_value}"
