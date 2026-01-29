#!/usr/bin/env python3
"""Render Vue components in markdown to static content for version archives.

This script transforms Vue components in markdown files to static markdown tables,
making archived documentation fully self-contained without requiring Vue/VitePress
to dynamically load JSON data.

Usage:
    python3 render_static_docs.py <version_directory>

Example:
    python3 render_static_docs.py site/versions/2.7.0
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def load_json(json_dir: Path, name: str) -> dict:
    """Load a plugin's JSON file.

    Args:
        json_dir: Directory containing JSON files
        name: Plugin name (without .json extension)

    Returns:
        Parsed JSON as dict, or empty dict if not found
    """
    json_file = json_dir / f"{name}.json"
    if json_file.exists():
        with open(json_file, encoding="utf-8") as f:
            return json.load(f)
    return {}


def format_arg(arg: dict) -> str:
    """Format a command argument for display.

    Args:
        arg: Argument dict with 'value' and 'required' keys

    Returns:
        Formatted argument string
    """
    if arg.get("required", False):
        return f"<{arg['value']}>"
    return f"[{arg['value']}]"


def escape_markdown(text: str) -> str:
    """Escape special markdown characters in table cells.

    Args:
        text: Raw text

    Returns:
        Escaped text safe for markdown tables
    """
    if not text:
        return ""
    # Escape pipe characters which break tables
    text = text.replace("|", "\\|")
    # Replace newlines with spaces (tables don't support multi-line cells)
    text = text.replace("\n", " ")
    return text


def render_command_table(commands: list) -> str:
    """Render commands as a markdown table.

    Args:
        commands: List of command dicts from JSON

    Returns:
        Markdown table string
    """
    if not commands:
        return "*No commands available.*\n"

    lines = [
        "| Command | Description |",
        "|---------|-------------|",
    ]

    for cmd in commands:
        name = cmd.get("name", "")
        args = cmd.get("args", [])
        description = escape_markdown(cmd.get("short_description", ""))

        # Build command with arguments
        if args:
            arg_str = " ".join(format_arg(arg) for arg in args)
            command_str = f"`{name} {arg_str}`"
        else:
            command_str = f"`{name}`"

        lines.append(f"| {command_str} | {description} |")

    return "\n".join(lines) + "\n"


def render_config_table(config: list, filter_names: list[str] | None = None) -> str:
    """Render config options as a 2-column markdown table.

    Args:
        config: List of config item dicts from JSON
        filter_names: Optional list of option names to include (base names without prefix)

    Returns:
        Markdown table string
    """
    if not config:
        return "*No configuration options.*\n"

    # Filter config items if filter is specified
    if filter_names:
        filtered = []
        for item in config:
            # Extract base name (strip [prefix]. if present)
            name = item.get("name", "")
            base_name = re.sub(r"^\[.*?\]\.", "", name)
            if base_name in filter_names:
                filtered.append(item)
        config = filtered

    if not config:
        return "*No configuration options.*\n"

    lines = [
        "| Option | Description |",
        "|--------|-------------|",
    ]

    for item in config:
        name = item.get("name", "")
        # Strip [prefix]. for display
        display_name = re.sub(r"^\[.*?\]\.", "", name)

        type_str = item.get("type", "")
        default = item.get("default")
        description = escape_markdown(item.get("description", ""))

        # Build option cell: `name` · type · =default · required/recommended
        option_parts = [f"`{display_name}`"]

        if type_str:
            option_parts.append(f"*{type_str}*")

        # Format default value
        if default is not None and default != "":
            if isinstance(default, bool):
                default_str = "`true`" if default else "`false`"
            elif isinstance(default, str):
                default_str = f'`"{default}"`'
            elif isinstance(default, (list, dict)):
                if len(default) > 0:
                    default_str = f"`{json.dumps(default)}`"
                else:
                    default_str = None
            else:
                default_str = f"`{default}`"
            if default_str:
                option_parts.append(f"={default_str}")

        # Add badges for required/recommended
        if item.get("required"):
            option_parts.append("**required**")
        elif item.get("recommended"):
            option_parts.append("*recommended*")

        option_cell = " · ".join(option_parts)

        # Add choices to description if present
        choices = item.get("choices")
        if choices and len(choices) > 0:
            # Filter out empty strings
            valid_choices = [c for c in choices if c]
            if valid_choices:
                choices_str = " \\| ".join(f"`{c}`" for c in valid_choices)
                if description:
                    description += f" (options: {choices_str})"
                else:
                    description = f"Options: {choices_str}"

        lines.append(f"| {option_cell} | {description} |")

    return "\n".join(lines) + "\n"


def render_plugin_list(plugins: list) -> str:
    """Render plugin list as markdown.

    Args:
        plugins: List of plugin dicts from index.json

    Returns:
        Markdown content
    """
    if not plugins:
        return "*No plugins available.*\n"

    # Filter out internal plugins
    plugins = [p for p in plugins if p.get("name") != "pyprland"]

    # Sort by name
    plugins = sorted(plugins, key=lambda p: p.get("name", ""))

    lines = []
    for plugin in plugins:
        name = plugin.get("name", "")
        description = plugin.get("description", "")
        stars = plugin.get("stars", 0)
        environments = plugin.get("environments", [])

        # Build star string
        star_str = "⭐" * stars if stars > 0 else ""

        # Build environment badges
        env_str = ""
        if environments:
            env_str = " " + " ".join(f"[{env}]" for env in environments)

        lines.append(f"- **[{name}](./{name}.md)**{star_str}{env_str}: {description}")

    return "\n".join(lines) + "\n"


def render_builtin_commands(commands: list) -> str:
    """Render built-in commands as a markdown table.

    Args:
        commands: List of command dicts from builtins.json

    Returns:
        Markdown table string
    """
    return render_command_table(commands)


def replace_plugin_commands(content: str, json_dir: Path) -> str:
    """Replace <PluginCommands plugin="X" /> with static table.

    Args:
        content: Markdown content
        json_dir: Directory containing JSON files

    Returns:
        Modified content with static tables
    """
    pattern = r'<PluginCommands\s+plugin=["\']([^"\']+)["\']\s*/>'

    def replacer(match: re.Match) -> str:
        plugin_name = match.group(1)
        data = load_json(json_dir, plugin_name)
        commands = data.get("commands", [])
        return render_command_table(commands)

    return re.sub(pattern, replacer, content)


def replace_plugin_config(content: str, json_dir: Path) -> str:
    """Replace <PluginConfig plugin="X" ... /> with static table.

    Args:
        content: Markdown content
        json_dir: Directory containing JSON files

    Returns:
        Modified content with static tables
    """
    # Match PluginConfig with various attributes
    # Examples:
    #   <PluginConfig plugin="expose" linkPrefix="config-" />
    #   <PluginConfig plugin="scratchpads" :filter="['command', 'class']" />
    pattern = r"<PluginConfig\s+([^>]*)/>"

    def replacer(match: re.Match) -> str:
        attrs_str = match.group(1)

        # Extract plugin name
        plugin_match = re.search(r'plugin=["\']([^"\']+)["\']', attrs_str)
        if not plugin_match:
            return match.group(0)  # Return unchanged if no plugin found
        plugin_name = plugin_match.group(1)

        # Extract filter if present
        filter_names = None
        filter_match = re.search(r':filter="\[([^\]]*)\]"', attrs_str)
        if filter_match:
            # Parse the filter array: 'command', 'class', ...
            filter_str = filter_match.group(1)
            filter_names = re.findall(r"'([^']+)'", filter_str)

        data = load_json(json_dir, plugin_name)
        config = data.get("config", [])
        return render_config_table(config, filter_names)

    return re.sub(pattern, replacer, content)


def replace_plugin_list(content: str, json_dir: Path) -> str:
    """Replace <PluginList /> or <PluginList/> with static content.

    Args:
        content: Markdown content
        json_dir: Directory containing JSON files

    Returns:
        Modified content
    """
    pattern = r"<PluginList\s*/>"

    def replacer(match: re.Match) -> str:
        data = load_json(json_dir, "index")
        plugins = data.get("plugins", [])
        return render_plugin_list(plugins)

    return re.sub(pattern, replacer, content)


def replace_builtin_commands(content: str, json_dir: Path) -> str:
    """Replace <BuiltinCommands /> with static table.

    Args:
        content: Markdown content
        json_dir: Directory containing JSON files

    Returns:
        Modified content
    """
    pattern = r"<BuiltinCommands\s*/>"

    def replacer(match: re.Match) -> str:
        data = load_json(json_dir, "builtins")
        commands = data.get("commands", [])
        return render_builtin_commands(commands)

    return re.sub(pattern, replacer, content)


def replace_config_badges(content: str, json_dir: Path) -> str:
    """Replace <ConfigBadges plugin="X" option="Y" /> with static inline badges.

    Args:
        content: Markdown content
        json_dir: Directory containing JSON files

    Returns:
        Modified content
    """
    pattern = r'<ConfigBadges\s+plugin=["\']([^"\']+)["\']\s+option=["\']([^"\']+)["\']\s*/>'

    def replacer(match: re.Match) -> str:
        plugin_name = match.group(1)
        option_name = match.group(2)

        data = load_json(json_dir, plugin_name)
        config = data.get("config", [])

        # Find the option - handle both "option" and "[prefix].option" formats
        item = None
        for c in config:
            base_name = re.sub(r"^\[.*?\]\.", "", c.get("name", ""))
            if base_name == option_name or c.get("name") == option_name:
                item = c
                break

        if not item:
            return f"*option not found*"

        # Build inline badges: *type* · =`"default"` · **required**
        parts = []

        type_str = item.get("type", "")
        if type_str:
            parts.append(f"*{type_str}*")

        # Format default value
        default = item.get("default")
        if default is not None and default != "":
            if isinstance(default, bool):
                default_str = "`true`" if default else "`false`"
            elif isinstance(default, str):
                default_str = f'`"{default}"`'
            elif isinstance(default, (list, dict)):
                if len(default) > 0:
                    default_str = f"`{json.dumps(default)}`"
                else:
                    default_str = None
            else:
                default_str = f"`{default}`"
            if default_str:
                parts.append(f"={default_str}")

        # Add badges for required/recommended
        if item.get("required"):
            parts.append("**required**")
        elif item.get("recommended"):
            parts.append("*recommended*")

        return " · ".join(parts)

    return re.sub(pattern, replacer, content)


def remove_script_setup(content: str) -> str:
    """Remove <script setup>...</script> blocks.

    Args:
        content: Markdown content

    Returns:
        Content with script blocks removed
    """
    # Match <script setup>...</script> including multiline
    pattern = r"<script\s+setup>.*?</script>\s*"
    return re.sub(pattern, "", content, flags=re.DOTALL)


def render_static_docs(version_dir: Path) -> None:
    """Transform all markdown files in version_dir to static content.

    Args:
        version_dir: Path to the version directory (e.g., site/versions/2.7.0)
    """
    json_dir = version_dir / "generated"

    if not json_dir.exists():
        print(f"Error: JSON directory not found: {json_dir}")
        sys.exit(1)

    md_files = list(version_dir.glob("*.md"))
    print(f"Processing {len(md_files)} markdown files in {version_dir}")

    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        original_content = content

        # Apply all transformations
        content = remove_script_setup(content)
        content = replace_plugin_commands(content, json_dir)
        content = replace_plugin_config(content, json_dir)
        content = replace_plugin_list(content, json_dir)
        content = replace_builtin_commands(content, json_dir)
        content = replace_config_badges(content, json_dir)

        # Only write if content changed
        if content != original_content:
            md_file.write_text(content, encoding="utf-8")
            print(f"  Rendered: {md_file.name}")
        else:
            print(f"  Unchanged: {md_file.name}")

    print("Done!")


def main() -> None:
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: render_static_docs.py <version_directory>")
        print("Example: render_static_docs.py site/versions/2.7.0")
        sys.exit(1)

    version_dir = Path(sys.argv[1])
    if not version_dir.is_dir():
        print(f"Error: Not a directory: {version_dir}")
        sys.exit(1)

    render_static_docs(version_dir)


if __name__ == "__main__":
    main()
