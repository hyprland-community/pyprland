#!/usr/bin/env python3
"""Generate JSON documentation for pyprland plugins.

This script extracts documentation from plugin source code:
- Configuration schema (from config_schema class attribute)
- Commands (from run_* methods and their docstrings)
- Plugin metadata (description, environments)

Output is written to site/generated/ as JSON files.
"""

from __future__ import annotations

import importlib
import inspect
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Add the project root to the path so we can import pyprland modules
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Paths
PLUGINS_DIR = PROJECT_ROOT / "pyprland" / "plugins"
OUTPUT_DIR = PROJECT_ROOT / "site" / "generated"
METADATA_FILE = PROJECT_ROOT / "scripts" / "plugin_metadata.json"

# Plugins to skip (not real plugins)
SKIP_PLUGINS = {"interface", "protocols", "__init__", "experimental"}

# Plugins that are packages (directories with __init__.py)
PACKAGE_PLUGINS = {"scratchpads", "monitors", "wallpapers", "pyprland"}


@dataclass
class ConfigItem:
    """A configuration field extracted from a plugin."""

    name: str
    type: str
    required: bool = False
    recommended: bool = False
    default: Any = None
    description: str = ""
    choices: list[str] | None = None


@dataclass
class CommandItem:
    """A command extracted from a plugin."""

    name: str
    signature: str
    short_description: str
    full_description: str


@dataclass
class PluginDoc:
    """Complete documentation for a plugin."""

    name: str
    description: str
    environments: list[str]
    commands: list[CommandItem] = field(default_factory=list)
    config: list[ConfigItem] = field(default_factory=list)


def extract_config_from_schema(schema: list) -> list[ConfigItem]:
    """Extract configuration items from a config_schema list.

    Args:
        schema: List of ConfigField objects

    Returns:
        List of ConfigItem dataclasses
    """
    config_items = []
    for field_def in schema:
        # Handle default value serialization
        default = field_def.default
        if default is not None and not isinstance(default, (str, int, float, bool, list, dict)):
            default = str(default)

        config_items.append(
            ConfigItem(
                name=field_def.name,
                type=field_def.type_name,
                required=field_def.required,
                recommended=getattr(field_def, "recommended", False),
                default=default,
                description=field_def.description,
                choices=field_def.choices,
            )
        )
    return config_items


def parse_command_docstring(docstring: str, method_name: str) -> tuple[str, str, str]:
    """Parse a command method's docstring to extract signature, short and full descriptions.

    The first line of the docstring often contains the signature like:
    "<arg> Short description" or "[optional_arg] Short description"

    Args:
        docstring: The raw docstring
        method_name: The method name (without run_ prefix)

    Returns:
        Tuple of (signature, short_description, full_description)
    """
    if not docstring:
        return method_name, "No description available.", ""

    lines = docstring.strip().split("\n")
    first_line = lines[0].strip()

    # Check if first line starts with argument spec like <arg>, [arg], or is just description
    # Pattern: optional leading args in <> or [], then the description
    arg_pattern = r"^((?:\[[\w\s\-]+\]|\<[\w\s\-]+\>)\s*)*(.*)$"
    match = re.match(arg_pattern, first_line)

    if match:
        args_part = match.group(1) or ""
        desc_part = match.group(2) or first_line

        # Build signature from method name and extracted args
        args_part = args_part.strip()
        if args_part:
            signature = f"{method_name} {args_part}"
        else:
            signature = method_name

        short_description = desc_part.strip() if desc_part.strip() else first_line
    else:
        signature = method_name
        short_description = first_line

    # Full description is the entire docstring
    full_description = docstring.strip()

    return signature, short_description, full_description


def extract_commands(extension_class: type) -> list[CommandItem]:
    """Extract command documentation from a plugin's Extension class.

    Args:
        extension_class: The Extension class from a plugin module

    Returns:
        List of CommandItem dataclasses
    """
    commands = []

    for name in dir(extension_class):
        if not name.startswith("run_"):
            continue

        method = getattr(extension_class, name)
        if not callable(method):
            continue

        command_name = name[4:]  # Remove 'run_' prefix
        docstring = inspect.getdoc(method) or ""

        signature, short_desc, full_desc = parse_command_docstring(docstring, command_name)

        commands.append(
            CommandItem(
                name=command_name,
                signature=signature,
                short_description=short_desc,
                full_description=full_desc,
            )
        )

    return commands


def get_plugin_description(extension_class: type) -> str:
    """Get the description from a plugin's Extension class docstring."""
    doc = inspect.getdoc(extension_class)
    if doc:
        # Return first line/sentence as description
        return doc.split("\n")[0].strip()
    return ""


def check_menu_mixin(extension_class: type) -> list:
    """Check if the plugin uses MenuMixin and return its schema if so.

    Args:
        extension_class: The Extension class

    Returns:
        List of ConfigField from MenuMixin, or empty list
    """
    # Check class hierarchy for MenuMixin
    for base in extension_class.__mro__:
        if base.__name__ == "MenuMixin":
            # Import MenuMixin's schema
            from pyprland.adapters.menus import MenuMixin

            return list(MenuMixin.menu_config_schema)
    return []


def load_scratchpads_schema() -> list:
    """Load the scratchpads-specific schema from schema.py."""
    from pyprland.plugins.scratchpads.schema import SCRATCHPAD_SCHEMA

    return list(SCRATCHPAD_SCHEMA)


def discover_plugins() -> list[str]:
    """Discover all available plugins.

    Returns:
        List of plugin names
    """
    plugins = []

    for item in PLUGINS_DIR.iterdir():
        if item.name.startswith("_"):
            continue

        if item.is_file() and item.suffix == ".py":
            name = item.stem
            if name not in SKIP_PLUGINS:
                plugins.append(name)
        elif item.is_dir() and (item / "__init__.py").exists():
            if item.name not in SKIP_PLUGINS:
                plugins.append(item.name)

    return sorted(plugins)


def load_plugin(plugin_name: str) -> PluginDoc | None:
    """Load a plugin and extract its documentation.

    Args:
        plugin_name: Name of the plugin to load

    Returns:
        PluginDoc dataclass or None if loading failed
    """
    try:
        module = importlib.import_module(f"pyprland.plugins.{plugin_name}")
    except ImportError as e:
        print(f"  Warning: Could not import {plugin_name}: {e}")
        return None

    if not hasattr(module, "Extension"):
        print(f"  Warning: {plugin_name} has no Extension class")
        return None

    extension_class = module.Extension

    # Get basic info
    description = get_plugin_description(extension_class)
    environments = getattr(extension_class, "environments", [])

    # Extract commands
    commands = extract_commands(extension_class)

    # Extract configuration schema
    config_items = []

    # Check for config_schema on the class
    config_schema = getattr(extension_class, "config_schema", [])
    if config_schema:
        config_items.extend(extract_config_from_schema(config_schema))

    # Check for MenuMixin schema
    menu_schema = check_menu_mixin(extension_class)
    if menu_schema:
        # Add menu config items, avoiding duplicates
        existing_names = {c.name for c in config_items}
        for field_def in menu_schema:
            if field_def.name not in existing_names:
                config_items.extend(extract_config_from_schema([field_def]))

    # Special case: scratchpads has per-scratchpad schema
    if plugin_name == "scratchpads":
        # Add a special marker for the scratchpad item schema
        scratchpad_schema = load_scratchpads_schema()
        # We'll add these as a nested structure
        # For now, add them with a prefix indicator
        for field_def in scratchpad_schema:
            item = ConfigItem(
                name=f"[scratchpad].{field_def.name}",
                type=field_def.type_name,
                required=field_def.required,
                recommended=getattr(field_def, "recommended", False),
                default=field_def.default,
                description=field_def.description,
                choices=field_def.choices,
            )
            config_items.append(item)

    return PluginDoc(
        name=plugin_name,
        description=description,
        environments=environments,
        commands=commands,
        config=config_items,
    )


def load_metadata() -> dict[str, dict]:
    """Load the editorial metadata file."""
    if METADATA_FILE.exists():
        with open(METADATA_FILE) as f:
            return json.load(f)
    return {}


def generate_plugin_json(plugin_doc: PluginDoc) -> dict:
    """Convert a PluginDoc to a JSON-serializable dict."""
    return {
        "name": plugin_doc.name,
        "description": plugin_doc.description,
        "environments": plugin_doc.environments,
        "commands": [asdict(cmd) for cmd in plugin_doc.commands],
        "config": [asdict(cfg) for cfg in plugin_doc.config],
    }


def generate_menu_json() -> dict:
    """Generate JSON for the Menu capability (shared by menu-based plugins).

    Returns:
        Dict ready for JSON serialization
    """
    from pyprland.adapters.menus import MenuMixin, every_menu_engine

    config_items = extract_config_from_schema(MenuMixin.menu_config_schema)

    # Extract engine default parameters from the implementation
    engine_defaults = {engine.proc_name: engine.proc_extra_parameters for engine in every_menu_engine}

    return {
        "name": "menu",
        "description": "Shared configuration for menu-based plugins.",
        "environments": [],
        "commands": [],
        "config": [asdict(cfg) for cfg in config_items],
        "engine_defaults": engine_defaults,
    }


def generate_builtins_json() -> dict:
    """Generate JSON for built-in commands from builtin_commands.py.

    Returns:
        Dict ready for JSON serialization
    """
    from pyprland.builtin_commands import BUILTIN_COMMANDS

    commands = []
    for name, (short_desc, detail, subcommands) in BUILTIN_COMMANDS.items():
        commands.append(
            {
                "name": name,
                "short_description": short_desc,
                "detail": detail,
                "subcommands": subcommands,
            }
        )

    return {"commands": commands}


def generate_index_json(plugin_docs: list[PluginDoc], metadata: dict) -> dict:
    """Generate the index.json with all plugins.

    Args:
        plugin_docs: List of PluginDoc dataclasses
        metadata: Editorial metadata dict

    Returns:
        Dict ready for JSON serialization
    """
    plugins = []
    for doc in plugin_docs:
        plugin_meta = metadata.get(doc.name, {})
        plugins.append(
            {
                "name": doc.name,
                "description": doc.description,
                "environments": doc.environments,
                "stars": plugin_meta.get("stars", 0),
                "demoVideoId": plugin_meta.get("demoVideoId"),
                "multimon": plugin_meta.get("multimon", False),
            }
        )

    # Sort by stars (descending), then name (ascending)
    plugins.sort(key=lambda p: (-p["stars"], p["name"]))

    return {"plugins": plugins}


def main():
    """Main entry point."""
    print("Generating plugin documentation...")

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Discover and load plugins
    plugin_names = discover_plugins()
    print(f"Found {len(plugin_names)} plugins: {', '.join(plugin_names)}")

    # Load metadata
    metadata = load_metadata()
    print(f"Loaded metadata for {len(metadata)} plugins")

    # Process each plugin
    plugin_docs = []
    for plugin_name in plugin_names:
        print(f"Processing {plugin_name}...")
        doc = load_plugin(plugin_name)
        if doc:
            plugin_docs.append(doc)

            # Write individual plugin JSON
            output_file = OUTPUT_DIR / f"{plugin_name}.json"
            with open(output_file, "w") as f:
                json.dump(generate_plugin_json(doc), f, indent=2)
                f.write("\n")
            print(f"  -> {output_file.relative_to(PROJECT_ROOT)}")

    # Generate index.json
    index_file = OUTPUT_DIR / "index.json"
    with open(index_file, "w") as f:
        json.dump(generate_index_json(plugin_docs, metadata), f, indent=2)
        f.write("\n")
    print(f"Generated index: {index_file.relative_to(PROJECT_ROOT)}")

    # Generate menu.json for Menu capability
    menu_file = OUTPUT_DIR / "menu.json"
    with open(menu_file, "w") as f:
        json.dump(generate_menu_json(), f, indent=2)
        f.write("\n")
    print(f"Generated menu capability: {menu_file.relative_to(PROJECT_ROOT)}")

    # Generate builtins.json for built-in commands
    builtins_file = OUTPUT_DIR / "builtins.json"
    with open(builtins_file, "w") as f:
        json.dump(generate_builtins_json(), f, indent=2)
        f.write("\n")
    print(f"Generated builtins: {builtins_file.relative_to(PROJECT_ROOT)}")

    print(f"\nDone! Generated documentation for {len(plugin_docs)} plugins.")


if __name__ == "__main__":
    main()
