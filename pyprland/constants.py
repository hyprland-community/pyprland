"""Shared constants for pyprland."""

import os
from pathlib import Path

from .common import IPC_FOLDER

__all__ = [
    "CONFIG_FILE",
    "CONTROL",
    "DEFAULT_NOTIFICATION_DURATION_MS",
    "DEFAULT_PALETTE_COLOR_RGB",
    "DEFAULT_REFRESH_RATE_HZ",
    "DEFAULT_WALLPAPER_HEIGHT",
    "DEFAULT_WALLPAPER_WIDTH",
    "DEMO_NOTIFICATION_DURATION_MS",
    "ERROR_NOTIFICATION_DURATION_MS",
    "IPC_MAX_RETRIES",
    "IPC_RETRY_DELAY_MULTIPLIER",
    "LEGACY_CONFIG_FILE",
    "MIGRATION_NOTIFICATION_DURATION_MS",
    "MIN_CLIENTS_FOR_LAYOUT",
    "OLD_CONFIG_FILE",
    "PREFETCH_MAX_RETRIES",
    "PREFETCH_RETRY_BASE_SECONDS",
    "PREFETCH_RETRY_MAX_SECONDS",
    "PYPR_DEMO",
    "SECONDS_PER_DAY",
    "SUPPORTED_SHELLS",
    "TASK_TIMEOUT",
]

CONTROL = f"{IPC_FOLDER}/.pyprland.sock"

# Config file paths - use XDG_CONFIG_HOME with fallback to ~/.config
_xdg_config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
OLD_CONFIG_FILE = _xdg_config_home / "hypr" / "pyprland.json"  # Very old JSON format
LEGACY_CONFIG_FILE = _xdg_config_home / "hypr" / "pyprland.toml"  # Old TOML location
CONFIG_FILE = _xdg_config_home / "pypr" / "config.toml"  # New canonical location

TASK_TIMEOUT = 35.0

PYPR_DEMO = os.environ.get("PYPR_DEMO")

# Supported shells for completion generation
SUPPORTED_SHELLS = ("bash", "zsh", "fish")

# Notification durations (milliseconds)
DEFAULT_NOTIFICATION_DURATION_MS = 5000
ERROR_NOTIFICATION_DURATION_MS = 8000
DEMO_NOTIFICATION_DURATION_MS = 4000
MIGRATION_NOTIFICATION_DURATION_MS = 15000

# Display defaults
DEFAULT_REFRESH_RATE_HZ = 60.0

# IPC retry settings
IPC_MAX_RETRIES = 3
IPC_RETRY_DELAY_MULTIPLIER = 0.5

# Layout thresholds
MIN_CLIENTS_FOR_LAYOUT = 2

# Time constants
SECONDS_PER_DAY = 86400

# Wallpapers defaults
DEFAULT_WALLPAPER_WIDTH = 1920
DEFAULT_WALLPAPER_HEIGHT = 1080
DEFAULT_PALETTE_COLOR_RGB = (66, 133, 244)  # Google Blue #4285F4

# Wallpapers prefetch retry settings
PREFETCH_RETRY_BASE_SECONDS = 2
PREFETCH_RETRY_MAX_SECONDS = 60
PREFETCH_MAX_RETRIES = 10
