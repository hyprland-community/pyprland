"""Main wizard flow for pypr-quickstart."""

from __future__ import annotations

from typing import TYPE_CHECKING

import questionary
from questionary import Choice

from .discovery import PluginInfo, discover_plugins, filter_by_environment
from .generator import (
    backup_config,
    generate_toml,
    get_config_path,
    load_existing_config,
    write_config,
)
from .helpers import detect_running_environment
from .helpers.monitors import ask_monitor_layout, detect_monitors
from .helpers.scratchpads import ask_scratchpads, scratchpad_to_dict
from .questions import ask_plugin_options

if TYPE_CHECKING:
    from pathlib import Path

# Max description length before truncation
MAX_DESC_LENGTH = 60


def print_banner() -> None:
    """Print the wizard banner."""
    questionary.print("\n╭─────────────────────────────────────╮", style="bold fg:cyan")
    questionary.print("│     Pyprland Quickstart Wizard      │", style="bold fg:cyan")
    questionary.print("╰─────────────────────────────────────╯\n", style="bold fg:cyan")


def ask_environment() -> str | None:
    """Ask user to select their environment.

    Returns:
        "hyprland", "niri", "other", or None if cancelled
    """
    detected = detect_running_environment()

    choices = [
        Choice(title="Hyprland", value="hyprland"),
        Choice(title="Niri", value="niri"),
        Choice(title="Other / Not running", value="other"),
    ]

    # If detected, move it to top and mark as detected
    if detected:
        choices = [c for c in choices if c.value != detected]
        choices.insert(
            0,
            Choice(
                title=f"{detected.capitalize()} (detected)",
                value=detected,
            ),
        )
        questionary.print(f"Detected: {detected.capitalize()}", style="fg:green")

    result = questionary.select(
        "Which compositor are you using?",
        choices=choices,
        default=detected or "hyprland",
    ).ask()
    if result is None:
        return None
    return str(result)


def ask_plugins(plugins: list[PluginInfo]) -> list[PluginInfo]:
    """Ask user to select plugins to configure.

    Args:
        plugins: Available plugins for the environment

    Returns:
        List of selected plugins
    """
    if not plugins:
        questionary.print("No plugins available for your environment.", style="fg:yellow")
        return []

    questionary.print("\nAvailable plugins:", style="bold")

    choices = []
    for plugin in plugins:
        desc = plugin.description or "No description"
        # Truncate long descriptions
        if len(desc) > MAX_DESC_LENGTH:
            desc = desc[: MAX_DESC_LENGTH - 3] + "..."
        choices.append(
            Choice(
                title=f"{plugin.name}: {desc}",
                value=plugin.name,
            )
        )

    selected_names = questionary.checkbox(
        "Which plugins would you like to enable?",
        choices=choices,
    ).ask()

    if selected_names is None:
        return []

    return [p for p in plugins if p.name in selected_names]


def configure_scratchpads(plugin: PluginInfo, environment: str) -> dict:
    """Run the scratchpads configuration wizard.

    Args:
        plugin: Plugin info (unused, for consistent signature)
        environment: Current environment (unused, for consistent signature)

    Returns:
        Scratchpads section config dict
    """
    _ = plugin, environment  # Unused, but required for consistent handler signature

    questionary.print("\n── Scratchpads Configuration ──", style="bold")

    scratchpads = ask_scratchpads()

    if not scratchpads:
        return {}

    config = {}
    for scratch in scratchpads:
        config[scratch.name] = scratchpad_to_dict(scratch)

    return config


def configure_monitors(plugin: PluginInfo, environment: str) -> dict:
    """Run the monitors configuration wizard.

    Args:
        plugin: Plugin info (unused, for consistent signature)
        environment: Current environment

    Returns:
        Monitors plugin config
    """
    _ = plugin  # Unused, but required for consistent handler signature

    questionary.print("\n── Monitors Configuration ──", style="bold")

    monitors = detect_monitors(environment)
    return ask_monitor_layout(monitors)


# Plugin-specific configuration wizards
# Each handler takes (PluginInfo, environment) and returns config dict
PLUGIN_WIZARDS = {
    "scratchpads": configure_scratchpads,
    "monitors": configure_monitors,
}


def configure_plugin(plugin: PluginInfo, environment: str) -> dict:
    """Configure a single plugin.

    Args:
        plugin: Plugin to configure
        environment: Current environment

    Returns:
        Plugin configuration dict
    """
    # Use special wizard if available
    if plugin.name in PLUGIN_WIZARDS:
        return PLUGIN_WIZARDS[plugin.name](plugin, environment)

    # Generic configuration from schema
    if plugin.config_schema:
        return ask_plugin_options(plugin.name, plugin.config_schema)

    return {}


def handle_existing_config(config_path: Path) -> bool:
    """Handle existing configuration file.

    Args:
        config_path: Path to check

    Returns:
        True if should continue, False to abort
    """
    existing = load_existing_config(config_path)

    if existing:
        questionary.print(
            f"\nExisting config found at: {config_path}",
            style="fg:yellow",
        )

        action = questionary.select(
            "What would you like to do?",
            choices=[
                Choice(title="Create backup and overwrite", value="overwrite"),
                Choice(title="Merge with existing config", value="merge"),
                Choice(title="Cancel", value="cancel"),
            ],
        ).ask()

        if action == "cancel" or action is None:
            return False

        if action == "overwrite":
            backup_path = backup_config(config_path)
            if backup_path:
                questionary.print(f"Backup created: {backup_path}", style="fg:green")

    return True


def build_config(
    plugins: list[PluginInfo],
    environment: str,
) -> dict:
    """Build the full configuration dictionary.

    Args:
        plugins: Selected plugins
        environment: Current environment

    Returns:
        Complete configuration dict
    """
    config = {
        "pyprland": {
            "plugins": [p.name for p in plugins],
        },
    }

    for plugin in plugins:
        plugin_config = configure_plugin(plugin, environment)
        if plugin_config:
            config[plugin.name] = plugin_config

    return config


def run_wizard(
    plugins: list[str] | None = None,
    dry_run: bool = False,
    output: Path | None = None,
) -> None:
    """Run the configuration wizard.

    Args:
        plugins: Pre-selected plugin names (skips plugin selection)
        dry_run: If True, only preview config without writing
        output: Custom output path
    """
    print_banner()

    # Step 1: Environment selection
    environment = ask_environment()
    if environment is None:
        return

    # Step 2: Discover and filter plugins
    all_plugins = discover_plugins()
    compatible_plugins = filter_by_environment(all_plugins, environment)

    # Step 3: Plugin selection
    if plugins:
        # Use pre-selected plugins
        selected = [p for p in compatible_plugins if p.name in plugins]
        if not selected:
            questionary.print(
                f"None of the specified plugins ({', '.join(plugins)}) are available.",
                style="fg:red",
            )
            return
    else:
        selected = ask_plugins(compatible_plugins)

    if not selected:
        questionary.print("No plugins selected. Exiting.", style="fg:yellow")
        return

    # Step 4: Check existing config
    config_path = output or get_config_path()
    if not dry_run and not handle_existing_config(config_path):
        return

    # Step 5: Configure each plugin
    config = build_config(selected, environment)

    # Step 6: Preview / write
    if dry_run:
        questionary.print("\n── Generated Configuration (dry-run) ──", style="bold")
        print(generate_toml(config))
    else:
        path, _content = write_config(config, output)
        questionary.print(f"\n✓ Configuration written to: {path}", style="fg:green bold")
        questionary.print("\nTo start pyprland, run:", style="bold")
        questionary.print("  pypr", style="fg:cyan")

    # Step 7: Show keybind hints for scratchpads
    if any(p.name == "scratchpads" for p in selected):
        _show_keybind_hints(config.get("scratchpads", {}), environment)


def _show_keybind_hints(scratchpads_config: dict, environment: str) -> None:
    """Show keybind hints for configured scratchpads.

    Args:
        scratchpads_config: Scratchpads configuration
        environment: Current environment
    """
    if not scratchpads_config:
        return

    questionary.print("\n── Suggested Keybindings ──", style="bold")

    if environment == "hyprland":
        questionary.print("Add to ~/.config/hypr/hyprland.conf:", style="fg:gray")
        for name in scratchpads_config:
            questionary.print(f"  bind = $mainMod, KEY, exec, pypr toggle {name}", style="fg:cyan")
    elif environment == "niri":
        questionary.print("Add to ~/.config/niri/config.kdl:", style="fg:gray")
        for name in scratchpads_config:
            questionary.print(f'  Mod+KEY {{ spawn "pypr" "toggle" "{name}"; }}', style="fg:cyan")

    questionary.print("\nReplace KEY with your preferred key (e.g., grave, F1, etc.)", style="fg:gray")
