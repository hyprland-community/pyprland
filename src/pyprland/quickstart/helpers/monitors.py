"""Monitor detection and layout wizard."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass

import questionary

from ...models import Environment

# Minimum monitors needed for layout configuration
MIN_MONITORS_FOR_LAYOUT = 2


@dataclass
class DetectedMonitor:
    """Information about a detected monitor."""

    name: str
    width: int
    height: int
    scale: float = 1.0


def detect_monitors_hyprland() -> list[DetectedMonitor]:
    """Detect monitors via hyprctl.

    Returns:
        List of detected monitors, empty if detection fails
    """
    try:
        result = subprocess.run(
            ["hyprctl", "monitors", "-j"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return [
                DetectedMonitor(
                    name=m["name"],
                    width=m["width"],
                    height=m["height"],
                    scale=m.get("scale", 1.0),
                )
                for m in data
            ]
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    return []


def detect_monitors_niri() -> list[DetectedMonitor]:
    """Detect monitors via niri msg.

    Returns:
        List of detected monitors, empty if detection fails
    """
    try:
        result = subprocess.run(
            ["niri", "msg", "-j", "outputs"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            monitors = []
            for name, info in data.items():
                if info.get("current_mode") is not None:
                    mode_idx = info.get("current_mode", 0)
                    modes = info.get("modes", [])
                    mode = modes[mode_idx] if mode_idx < len(modes) else {}
                    monitors.append(
                        DetectedMonitor(
                            name=name,
                            width=mode.get("width", 0),
                            height=mode.get("height", 0),
                            scale=info.get("scale", 1.0),
                        )
                    )
            return monitors
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    return []


def detect_monitors(environment: str) -> list[DetectedMonitor]:
    """Detect monitors based on environment.

    Args:
        environment: "hyprland" or "niri"

    Returns:
        List of detected monitors
    """
    if environment == Environment.HYPRLAND:
        return detect_monitors_hyprland()
    if environment == Environment.NIRI:
        return detect_monitors_niri()
    return []


def ask_monitor_layout(monitors: list[DetectedMonitor]) -> dict:
    """Interactive monitor layout wizard.

    Asks the user about monitor arrangement and builds a placement config.

    Args:
        monitors: List of detected monitors

    Returns:
        Dict with placement configuration, empty if skipped or single monitor
    """
    if not monitors:
        questionary.print("No monitors detected. Skipping layout configuration.", style="fg:yellow")
        return {}

    # Show detected monitors
    questionary.print("\nDetected monitors:", style="bold")
    for m in monitors:
        questionary.print(f"  - {m.name} ({m.width}x{m.height}, scale {m.scale})")
    print()

    if len(monitors) < MIN_MONITORS_FOR_LAYOUT:
        questionary.print("Single monitor detected. No layout needed.", style="fg:ansigray")
        return {}

    # Ask layout type
    layout = questionary.select(
        "How should your monitors be arranged?",
        choices=[
            "Side by side (left to right)",
            "Side by side (right to left)",
            "Stacked (top to bottom)",
            "Stacked (bottom to top)",
            "Skip (configure manually)",
        ],
    ).ask()

    if layout is None or "Skip" in layout:
        return {}

    # Ask which monitor should be first
    monitor_names = [m.name for m in monitors]
    first = questionary.select(
        "Which monitor should be first (leftmost/topmost)?",
        choices=monitor_names,
    ).ask()

    if first is None:
        return {}

    # Build placement config
    # Order monitors: first one, then the rest
    order = [first, *[n for n in monitor_names if n != first]]

    # Determine direction based on layout choice
    if "left to right" in layout:
        direction = "rightof"
    elif "right to left" in layout:
        direction = "leftof"
    elif "top to bottom" in layout:
        direction = "bottomof"
    else:  # bottom to top
        direction = "topof"

    # Build placement: each monitor (except first) is placed relative to previous
    placement: dict[str, dict[str, str]] = {}
    for i, name in enumerate(order[1:], 1):
        placement[name] = {direction: order[i - 1]}

    return {"placement": placement}
