"""Standalone plugin discovery for the quickstart wizard."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyprland.validation import ConfigItems

PLUGINS_DIR = Path(__file__).parent.parent / "plugins"
SKIP_PLUGINS = {"interface", "protocols", "__init__", "experimental", "mixins"}


@dataclass
class PluginInfo:
    """Information about a discovered plugin."""

    name: str
    description: str
    config_schema: ConfigItems | None
    environments: list[str]


def discover_plugins() -> list[PluginInfo]:
    """Discover all available plugins.

    Scans the pyprland/plugins/ directory for plugin modules and packages,
    loading their metadata without instantiating them.

    Returns:
        List of PluginInfo for all discovered plugins, sorted by name
    """
    plugins = []

    for item in PLUGINS_DIR.iterdir():
        name = None
        if item.is_file() and item.suffix == ".py" and item.stem not in SKIP_PLUGINS:
            name = item.stem
        elif item.is_dir() and (item / "__init__.py").exists() and item.name not in SKIP_PLUGINS:
            name = item.name

        if name and name != "pyprland":
            try:
                info = load_plugin_info(name)
                if info:
                    plugins.append(info)
            except Exception:  # noqa: BLE001, S110  # pylint: disable=broad-exception-caught
                pass  # Skip plugins that fail to load - intentionally silent

    return sorted(plugins, key=lambda p: p.name)


def load_plugin_info(name: str) -> PluginInfo | None:
    """Load plugin metadata without instantiating.

    Args:
        name: Plugin module name

    Returns:
        PluginInfo if successful, None if plugin doesn't have Extension class
    """
    module = importlib.import_module(f"pyprland.plugins.{name}")
    extension_class = getattr(module, "Extension", None)

    if not extension_class:
        return None

    # Extract description from docstring
    doc = extension_class.__doc__ or ""
    description = doc.split("\n")[0].strip()

    # Get schema and environments
    schema = getattr(extension_class, "config_schema", None)
    environments = getattr(extension_class, "environments", [])

    return PluginInfo(
        name=name,
        description=description,
        config_schema=schema,
        environments=list(environments) if environments else [],
    )


def filter_by_environment(plugins: list[PluginInfo], environment: str) -> list[PluginInfo]:
    """Filter plugins by environment compatibility.

    Args:
        plugins: List of plugins to filter
        environment: Target environment ("hyprland", "niri", or "other")

    Returns:
        Filtered list of compatible plugins

    For "other" environment, only returns plugins with empty environments list.
    For "hyprland" or "niri", returns plugins that explicitly support that
    environment OR have an empty environments list (universal plugins).
    """
    if environment == "other":
        return [p for p in plugins if not p.environments]
    return [p for p in plugins if not p.environments or environment in p.environments]
