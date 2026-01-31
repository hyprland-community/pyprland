"""Shared utilities - re-exports from focused modules for backward compatibility.

This module aggregates exports from specialized modules (debug, ipc_paths,
logging_setup, state, terminal, utils) providing a single import point
for commonly used functions and classes.

Note: For new code, prefer importing directly from the specific modules.
"""

# Re-export from focused modules
from .debug import DEBUG, is_debug, set_debug
from .ipc_paths import (
    HYPRLAND_INSTANCE_SIGNATURE,
    IPC_FOLDER,
    MINIMUM_ADDR_LEN,
    MINIMUM_FULL_ADDR_LEN,
    init_ipc_folder,
)
from .logging_setup import LogObjects, get_logger, init_logger
from .state import SharedState
from .terminal import run_interactive_program, set_raw_mode, set_terminal_size
from .utils import apply_filter, apply_variables, is_rotated, merge, notify_send

__all__ = [
    "DEBUG",
    "HYPRLAND_INSTANCE_SIGNATURE",
    "IPC_FOLDER",
    "MINIMUM_ADDR_LEN",
    "MINIMUM_FULL_ADDR_LEN",
    "LogObjects",
    "SharedState",
    "apply_filter",
    "apply_variables",
    "get_logger",
    "init_ipc_folder",
    "init_logger",
    "is_debug",
    "is_rotated",
    "merge",
    "notify_send",
    "run_interactive_program",
    "set_debug",
    "set_raw_mode",
    "set_terminal_size",
]
