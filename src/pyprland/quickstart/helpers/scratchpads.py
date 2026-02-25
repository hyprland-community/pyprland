"""Scratchpad presets and configuration wizard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import questionary

from . import TERMINAL_COMMANDS, detect_app, detect_terminal, get_terminal_command

# Preset scratchpad configurations
# Each preset includes:
#   - label: Human-readable name
#   - detect: List of apps to detect (first found is used)
#   - needs_terminal: Whether app needs to run in terminal
#   - class_name: Window class to use for matching
#   - animation: Default animation direction
#   - size: Default size as percentage or absolute

SCRATCHPAD_PRESETS: dict[str, dict[str, Any]] = {
    "term": {
        "label": "Dropdown terminal",
        "detect": ["kitty", "alacritty", "foot", "wezterm", "gnome-terminal", "konsole"],
        "needs_terminal": False,  # It IS a terminal
        "class_name": "dropterm",
        "animation": "fromtop",
        "size": "75% 60%",
    },
    "files": {
        "label": "File manager",
        "detect": ["thunar", "nautilus", "dolphin", "pcmanfm", "nemo", "caja"],
        "needs_terminal": False,
        "class_name": "files-scratch",
        "animation": "fromright",
        "size": "60% 70%",
    },
    "music": {
        "label": "Music player",
        "detect": ["spotify", "rhythmbox", "clementine", "strawberry", "lollypop", "elisa"],
        "needs_terminal": False,
        "class_name": "music-scratch",
        "animation": "fromright",
        "size": "50% 60%",
    },
    "volume": {
        "label": "Volume mixer",
        "detect": ["pavucontrol", "pavucontrol-qt", "easyeffects"],
        "needs_terminal": False,
        "class_name": "volume-scratch",
        "animation": "fromright",
        "size": "40% 50%",
    },
    "monitor": {
        "label": "System monitor",
        "detect": ["btop", "htop", "top", "gotop", "gtop"],
        "needs_terminal": True,
        "class_name": "monitor-scratch",
        "animation": "fromtop",
        "size": "80% 70%",
    },
    "calc": {
        "label": "Calculator",
        "detect": ["qalculate-gtk", "gnome-calculator", "kcalc", "galculator", "speedcrunch"],
        "needs_terminal": False,
        "class_name": "calc-scratch",
        "animation": "fromright",
        "size": "30% 40%",
    },
    "notes": {
        "label": "Notes",
        "detect": ["obsidian", "logseq", "joplin", "simplenote", "standard-notes"],
        "needs_terminal": False,
        "class_name": "notes-scratch",
        "animation": "fromright",
        "size": "50% 70%",
    },
    "passwords": {
        "label": "Password manager",
        "detect": ["keepassxc", "bitwarden", "1password"],
        "needs_terminal": False,
        "class_name": "passwords-scratch",
        "animation": "fromright",
        "size": "40% 50%",
    },
}


@dataclass
class ScratchpadConfig:
    """Configuration for a single scratchpad."""

    name: str
    command: str
    class_name: str
    animation: str = "fromtop"
    size: str = "75% 60%"
    lazy: bool = True


def detect_available_presets() -> list[tuple[str, str, str]]:
    """Detect which preset apps are available on the system.

    Returns:
        List of tuples: (preset_name, label, detected_app)
    """
    available = []
    for name, preset in SCRATCHPAD_PRESETS.items():
        app = detect_app(preset["detect"])
        if app:
            available.append((name, preset["label"], app))
    return available


def build_command(
    app: str,
    class_name: str,
    needs_terminal: bool,
    terminal: str | None = None,
) -> str:
    """Build command string for a scratchpad.

    Args:
        app: Application to run
        class_name: Window class name
        needs_terminal: Whether app needs to run in terminal
        terminal: Terminal to use (if needs_terminal is True)

    Returns:
        Full command string
    """
    if needs_terminal:
        if not terminal:
            terminal = detect_terminal()
        if terminal and terminal in TERMINAL_COMMANDS:
            base = get_terminal_command(terminal, class_name)
            return f"{base} {app}"
        # Fallback
        return f"{terminal or 'xterm'} -e {app}"

    # Check if app is a terminal itself (for the "term" preset)
    if app in TERMINAL_COMMANDS:
        return get_terminal_command(app, class_name)

    # Regular app - just return app name (class detection will be by process)
    return app


def create_preset_config(
    preset_name: str,
    app: str,
    terminal: str | None = None,
) -> ScratchpadConfig:
    """Create a ScratchpadConfig from a preset.

    Args:
        preset_name: Name of the preset (key in SCRATCHPAD_PRESETS)
        app: Detected or user-specified application
        terminal: Terminal to use for terminal-based apps

    Returns:
        Configured ScratchpadConfig
    """
    preset = SCRATCHPAD_PRESETS[preset_name]

    command = build_command(
        app,
        preset["class_name"],
        preset["needs_terminal"],
        terminal,
    )

    return ScratchpadConfig(
        name=preset_name,
        command=command,
        class_name=preset["class_name"],
        animation=preset["animation"],
        size=preset["size"],
        lazy=True,
    )


def ask_scratchpads() -> list[ScratchpadConfig]:
    """Interactive wizard to configure scratchpads.

    Returns:
        List of ScratchpadConfig objects for selected scratchpads
    """
    # Detect available apps
    available = detect_available_presets()

    if not available:
        questionary.print(
            "No common scratchpad applications detected. You can add scratchpads manually later.",
            style="fg:yellow",
        )
        return []

    # Show available presets
    questionary.print("\nDetected applications for scratchpads:", style="bold")
    choices = []
    for name, label, app in available:
        choices.append(
            questionary.Choice(
                title=f"{label} ({app})",
                value=name,
                checked=name == "term",  # Pre-select terminal by default
            )
        )

    # Let user select which to configure
    selected = questionary.checkbox(
        "Which scratchpads would you like to set up?",
        choices=choices,
    ).ask()

    if selected is None:  # User cancelled
        return []

    if not selected:
        return []

    # Build configs for selected presets
    terminal = detect_terminal()
    configs = []

    for preset_name in selected:
        # Find the detected app for this preset
        found_app = next((a for n, _, a in available if n == preset_name), None)
        if found_app is not None:
            config = create_preset_config(preset_name, found_app, terminal)
            configs.append(config)

    return configs


def scratchpad_to_dict(config: ScratchpadConfig) -> dict:
    """Convert ScratchpadConfig to dict for TOML generation.

    Args:
        config: ScratchpadConfig object

    Returns:
        Dict representation for TOML
    """
    return {
        "command": config.command,
        "class": config.class_name,
        "animation": config.animation,
        "size": config.size,
        "lazy": config.lazy,
    }
