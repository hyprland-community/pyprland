"""Documentation formatting for pypr doc command.

Formats plugin and configuration documentation for terminal display
with ANSI colors and structured output. Uses runtime schema data to
ensure documentation is always accurate.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from .ansi import BOLD, CYAN, DIM, GREEN, colorize, should_colorize

if TYPE_CHECKING:
    from .commands.models import CommandInfo
    from .plugins.interface import Plugin
    from .validation import ConfigField, ConfigItems

__all__ = ["format_config_field_doc", "format_plugin_doc", "format_plugin_list"]


def _c(text: str, *codes: str) -> str:
    """Colorize text if stdout is a TTY."""
    if should_colorize(sys.stdout):
        return colorize(text, *codes)
    return text


def _format_default(value: Any) -> str:
    """Format a default value for display."""
    if isinstance(value, str):
        return f'"{value}"' if value else '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[]" if not value else str(value)
    if isinstance(value, dict):
        return "{}" if not value else str(value)
    return str(value)


def _get_plugin_description(plugin: Plugin) -> str:
    """Get the first line of plugin's docstring as description."""
    doc = getattr(plugin.__class__, "__doc__", "") or ""
    if doc:
        return doc.split("\n")[0].strip()
    return ""


def format_plugin_list(plugins: dict[str, Plugin]) -> str:
    """Format list of all plugins with descriptions.

    Args:
        plugins: Dict mapping plugin name to Plugin instance

    Returns:
        Formatted string listing all plugins
    """
    lines = [_c("AVAILABLE PLUGINS", BOLD), ""]

    # Sort by name, skip "pyprland" internal plugin
    for name in sorted(plugins.keys()):
        if name == "pyprland":
            continue
        plugin = plugins[name]
        desc = _get_plugin_description(plugin)

        # Get environments
        envs = getattr(plugin, "environments", [])
        env_str = f" [{', '.join(envs)}]" if envs else ""

        lines.append(f"  {_c(name, CYAN)}{_c(env_str, DIM)}")
        if desc:
            lines.append(f"      {desc}")

    lines.append("")
    lines.append("Use 'pypr doc <plugin>' for details.")
    return "\n".join(lines)


def format_plugin_doc(
    plugin: Plugin,
    commands: list[CommandInfo],
    schema_override: ConfigItems | None = None,
    config_prefix: str = "",
) -> str:
    """Format full plugin documentation.

    Args:
        plugin: The plugin instance
        commands: List of CommandInfo for the plugin's commands
        schema_override: Optional schema to use instead of plugin's config_schema
        config_prefix: Prefix for config option names (e.g., "[name]." for scratchpads)

    Returns:
        Formatted string with full plugin documentation
    """
    name = plugin.name.upper()
    lines = [_c(name, BOLD)]

    # Description from docstring
    desc = _get_plugin_description(plugin)
    if desc:
        lines.append(desc)

    # Environments
    envs = getattr(plugin, "environments", [])
    if envs:
        lines.append(f"\nEnvironments: {', '.join(envs)}")

    # Commands
    if commands:
        lines.append(f"\n{_c('COMMANDS', BOLD)}")
        for cmd in commands:
            args_str = " ".join(f"<{a.value}>" if a.required else f"[{a.value}]" for a in cmd.args)
            cmd_line = f"  {_c(cmd.name, GREEN)}"
            if args_str:
                cmd_line += f" {args_str}"
            lines.append(cmd_line)
            if cmd.short_description:
                lines.append(f"      {cmd.short_description}")

    # Configuration - use override if provided, otherwise get from plugin
    schema: ConfigItems | None = schema_override or getattr(plugin, "config_schema", None)
    if schema and len(schema) > 0:
        lines.append(f"\n{_c('CONFIGURATION', BOLD)}")
        if config_prefix:
            lines.append(f"  (Options are per-item, prefix with {config_prefix})")
        lines.extend(_format_config_section(schema))

    lines.append("")
    lines.append("Use 'pypr doc <plugin>.<option>' for option details.")
    return "\n".join(lines)


def _format_config_section(schema: ConfigItems) -> list[str]:
    """Format configuration fields grouped by category.

    Args:
        schema: ConfigItems containing all fields

    Returns:
        List of formatted lines
    """
    # Group by category
    by_category: dict[str, list[ConfigField]] = {}
    for field in schema:
        cat = field.category or "general"
        by_category.setdefault(cat, []).append(field)

    lines: list[str] = []
    for category, fields in by_category.items():
        lines.append(f"\n  {_c(category.title(), DIM, BOLD)}")
        for field in fields:
            lines.extend(_format_field_brief(field))

    return lines


def _format_field_brief(field: ConfigField) -> list[str]:
    """Format a config field in brief form.

    Args:
        field: The ConfigField to format

    Returns:
        List of formatted lines
    """
    # Name with type and flags
    flags = []
    if field.required:
        flags.append("required")
    elif field.recommended:
        flags.append("recommended")

    type_str = f"({field.type_name})"
    flag_str = f" [{', '.join(flags)}]" if flags else ""

    lines = [f"    {_c(field.name, CYAN)} {_c(type_str, DIM)}{flag_str}"]

    # Description
    if field.description:
        lines.append(f"        {field.description}")

    # Default (if not required and has one)
    if not field.required and field.default is not None:
        default_str = _format_default(field.default)
        lines.append(f"        Default: {default_str}")

    return lines


def _format_field_status(field: ConfigField) -> str:
    """Format the status line (required/recommended/optional)."""
    if field.required:
        return f"Status: {_c('required', GREEN)}"
    if field.recommended:
        return "Status: recommended"
    return "Status: optional"


def _format_field_choices(field: ConfigField) -> list[str]:
    """Format choices section if present."""
    if not field.choices:
        return []
    lines = [f"\n{_c('Choices:', BOLD)}"]
    for choice in field.choices:
        choice_str = f'"{choice}"' if isinstance(choice, str) else str(choice)
        lines.append(f"  - {choice_str}")
    return lines


def _format_field_children(field: ConfigField) -> list[str]:
    """Format nested options section if present."""
    if not field.children:
        return []
    lines = [f"\n{_c('Nested options:', BOLD)}"]
    for child in field.children:
        lines.append(f"  {child.name} ({child.type_name})")
        if child.description:
            lines.append(f"      {child.description}")
    return lines


def format_config_field_doc(plugin_name: str, field: ConfigField) -> str:
    """Format detailed documentation for a single config field.

    Args:
        plugin_name: Name of the plugin (for header)
        field: The ConfigField to document

    Returns:
        Formatted string with full field documentation
    """
    header = f"{plugin_name.upper()}.{field.name.upper()}"
    lines = [_c(header, BOLD), ""]

    # Type and status
    lines.append(f"Type: {_c(field.type_name, CYAN)}")
    lines.append(_format_field_status(field))

    # Default
    if field.default is not None or not field.required:
        default_str = _format_default(field.default)
        lines.append(f"Default: {default_str}")

    # Category
    if field.category:
        lines.append(f"Category: {field.category}")

    # Description
    lines.append("")
    lines.append(field.description or "(No description available)")

    # Choices and children
    lines.extend(_format_field_choices(field))
    lines.extend(_format_field_children(field))

    return "\n".join(lines)
