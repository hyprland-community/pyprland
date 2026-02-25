"""Configuration schema for the pyprland core plugin.

This module is separate to allow manager.py to import the schema
without circular import issues.
"""

from pathlib import Path

from pyprland.validation import ConfigField, ConfigItems

PYPRLAND_CONFIG_SCHEMA = ConfigItems(
    ConfigField("plugins", list, required=True, description="List of plugins to load", category="basic"),
    ConfigField(
        "include",
        list[Path],
        required=False,
        description="Additional config files or folders to include",
        category="basic",
        is_directory=True,
    ),
    ConfigField(
        "plugins_paths",
        list[Path],
        default=[],
        description="Additional paths to search for third-party plugins",
        category="basic",
        is_directory=True,
    ),
    ConfigField(
        "colored_handlers_log",
        bool,
        default=True,
        description="Enable colored log output for event handlers (debugging)",
        category="advanced",
    ),
    ConfigField(
        "notification_type",
        str,
        default="auto",
        description="Notification method: 'auto', 'notify-send', or 'native'",
        category="basic",
    ),
    ConfigField(
        "variables",
        dict,
        default={},
        description="User-defined variables for string substitution (see Variables page)",
        category="advanced",
    ),
    ConfigField(
        "hyprland_version",
        str,
        default="",
        description="Override auto-detected Hyprland version (e.g., '0.40.0')",
        category="advanced",
    ),
    ConfigField(
        "desktop",
        str,
        default="",
        description="Override auto-detected desktop environment (e.g., 'hyprland', 'niri'). Empty means auto-detect.",
        category="advanced",
    ),
)
