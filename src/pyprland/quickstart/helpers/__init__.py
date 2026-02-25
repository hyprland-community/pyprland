"""Shared helper utilities for the quickstart wizard."""

from __future__ import annotations

import shutil
import subprocess

from ...models import Environment

TERMINALS = ["kitty", "alacritty", "foot", "wezterm", "gnome-terminal", "konsole", "xterm"]

TERMINAL_COMMANDS: dict[str, str] = {
    "kitty": "kitty --class {class_name}",
    "alacritty": "alacritty --class {class_name}",
    "foot": "foot --app-id {class_name}",
    "wezterm": "wezterm start --class {class_name}",
    "gnome-terminal": "gnome-terminal --class={class_name}",
    "konsole": "konsole --name {class_name}",
    "xterm": "xterm -class {class_name}",
}


def detect_app(candidates: list[str]) -> str | None:
    """Return first installed app from candidates.

    Args:
        candidates: List of application names to check

    Returns:
        First found application name, or None if none installed
    """
    for app in candidates:
        if shutil.which(app):
            return app
    return None


def detect_terminal() -> str | None:
    """Detect installed terminal emulator.

    Returns:
        Name of first found terminal, or None
    """
    return detect_app(TERMINALS)


def get_terminal_command(terminal: str, class_name: str) -> str:
    """Get terminal command with class name substituted.

    Args:
        terminal: Terminal name
        class_name: Window class name to use

    Returns:
        Full command string with class name substituted
    """
    template = TERMINAL_COMMANDS.get(terminal, terminal)
    return template.format(class_name=class_name)


def detect_running_environment() -> Environment | None:
    """Auto-detect environment from running compositor.

    Checks for running Hyprland or Niri by trying their CLI tools.

    Returns:
        Environment.HYPRLAND, Environment.NIRI, or None if neither detected
    """
    # Try hyprctl
    try:
        result = subprocess.run(
            ["hyprctl", "version"],
            capture_output=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            return Environment.HYPRLAND
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Try niri
    try:
        result = subprocess.run(
            ["niri", "msg", "version"],
            capture_output=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            return Environment.NIRI
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None
