"""Shared constants for pyprland."""

import os

from .common import IPC_FOLDER

__all__ = [
    "CONTROL",
    "CONFIG_FILE",
    "OLD_CONFIG_FILE",
    "TASK_TIMEOUT",
    "PYPR_DEMO",
    "SUPPORTED_SHELLS",
    "DEFAULT_NOTIFICATION_DURATION_MS",
    "ERROR_NOTIFICATION_DURATION_MS",
    "DEMO_NOTIFICATION_DURATION_MS",
    "DEFAULT_REFRESH_RATE_HZ",
    "IPC_MAX_RETRIES",
    "IPC_RETRY_DELAY_MULTIPLIER",
    "MIN_CLIENTS_FOR_LAYOUT",
]

CONTROL = f"{IPC_FOLDER}/.pyprland.sock"
OLD_CONFIG_FILE = "~/.config/hypr/pyprland.json"
CONFIG_FILE = "~/.config/hypr/pyprland.toml"

TASK_TIMEOUT = 35.0

PYPR_DEMO = os.environ.get("PYPR_DEMO")

# Supported shells for completion generation
SUPPORTED_SHELLS = ("bash", "zsh", "fish")

# Notification durations (milliseconds)
DEFAULT_NOTIFICATION_DURATION_MS = 5000
ERROR_NOTIFICATION_DURATION_MS = 8000
DEMO_NOTIFICATION_DURATION_MS = 4000

# Display defaults
DEFAULT_REFRESH_RATE_HZ = 60.0

# IPC retry settings
IPC_MAX_RETRIES = 3
IPC_RETRY_DELAY_MULTIPLIER = 0.5

# Layout thresholds
MIN_CLIENTS_FOR_LAYOUT = 2
