"""Shared utilities: logging."""

import fcntl
import logging
import os
import pty
import re
import select
import struct
import subprocess
import sys
import termios
from dataclasses import dataclass, field
from typing import Any, cast

from .types import MonitorInfo, VersionInfo

__all__ = [
    "DEBUG",
    "apply_variables",
    "get_logger",
    "merge",
    "run_interactive_program",
    "state",
    "init_logger",
    "SharedState",
    "prepare_for_quotes",
    "apply_filter",
    "CastBoolMixin",
    "is_rotated",
]


DEBUG = os.environ.get("DEBUG", False)

HYPRLAND_INSTANCE_SIGNATURE = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "NO_INSTANCE")

MINIMUM_ADDR_LEN = 4

MAX_SOCKET_FILE_LEN = 15
MAX_SOCKET_PATH_LEN = 108

try:
    # May throw an OSError because AF_UNIX path is too long: try to work around it only if needed
    original_ipc_folder = (
        f'{os.environ["XDG_RUNTIME_DIR"]}/hypr/{HYPRLAND_INSTANCE_SIGNATURE}'
        if os.path.exists(f'{os.environ["XDG_RUNTIME_DIR"]}/hypr/{HYPRLAND_INSTANCE_SIGNATURE}')
        else f"/tmp/hypr/{HYPRLAND_INSTANCE_SIGNATURE}"  # noqa: S108
    )

    if len(original_ipc_folder) >= MAX_SOCKET_PATH_LEN - MAX_SOCKET_FILE_LEN:
        IPC_FOLDER = f"/tmp/.pypr-{HYPRLAND_INSTANCE_SIGNATURE}"  # noqa: S108
        # make a link from short path to original path
        if not os.path.exists(IPC_FOLDER):
            os.symlink(original_ipc_folder, IPC_FOLDER)
    else:
        IPC_FOLDER = original_ipc_folder

except KeyError:
    print("This is a fatal error, assuming we are running documentation generation or testing in a sandbox, hence ignoring it")
    IPC_FOLDER = "/"


def set_terminal_size(descriptor: int, rows: int, cols: int) -> None:
    """Set the terminal size."""
    fcntl.ioctl(descriptor, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))


def set_raw_mode(descriptor: int) -> None:
    """Set a file descriptor in raw mode."""
    # Get the current terminal attributes
    attrs = termios.tcgetattr(descriptor)
    # Set the terminal to raw mode
    attrs[3] &= ~termios.ICANON  # Disable canonical mode (line buffering)
    attrs[3] &= ~termios.ECHO  # Disable echoing of input characters
    termios.tcsetattr(descriptor, termios.TCSANOW, attrs)


def run_interactive_program(command: str) -> None:
    """Run an interactive program in a blocking way."""
    # Create a pseudo-terminal
    master, slave = pty.openpty()

    # Start the program in the pseudo-terminal
    process = subprocess.Popen(  # pylint: disable=consider-using-with
        command, shell=True, stdin=slave, stdout=slave, stderr=slave
    )

    # Close the slave end in the parent process
    os.close(slave)

    # Get the size of the real terminal
    rows, cols = os.popen("stty size", "r").read().split()

    # Set the terminal size for the pseudo-terminal
    set_terminal_size(master, int(rows), int(cols))

    # Set the terminal to raw mode
    set_raw_mode(sys.stdin.fileno())
    set_raw_mode(master)

    # Forward input from the real terminal to the program and vice versa
    try:
        while process.poll() is None:
            r, _, _ = select.select([sys.stdin, master], [], [])
            for fd in r:
                if fd == sys.stdin:
                    # Read input from the real terminal
                    user_input = os.read(sys.stdin.fileno(), 1024)
                    # Forward input to the program
                    os.write(master, user_input)
                elif fd == master:
                    # Read output from the program
                    output = os.read(master, 1024)
                    # Forward output to the real terminal
                    os.write(sys.stdout.fileno(), output)
    except OSError:
        pass
    finally:
        # Restore terminal settings
        termios.tcsetattr(sys.stdin, termios.TCSANOW, termios.tcgetattr(0))


def merge(merged: dict[str, Any], obj2: dict[str, Any]) -> dict[str, Any]:
    """Merge the content of d2 into d1.

    Args:
        merged (dict): Dictionary to merge into
        obj2 (dict): Dictionary to merge from

    Returns:
        `merged` dictionary with the merged content

    Eg:
        merge({"a": {"b": 1}}, {"a": {"c": 2}}) == {"a": {"b": 1, "c": 2}}

    """
    for key, value in obj2.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            # If both values are dictionaries, recursively merge them
            merge(merged[key], value)
        elif key in merged and isinstance(merged[key], list) and isinstance(value, list):
            # If both values are lists, concatenate them
            merged[key] += value
        else:
            # Otherwise, update the value or add the key-value pair
            merged[key] = value
    return merged


class LogObjects:
    """Reusable objects for loggers."""

    handlers: list[logging.Handler] = []


def init_logger(filename: str | None = None, force_debug: bool = False) -> None:
    """Initialize the logging system."""
    global DEBUG
    if force_debug:
        DEBUG = True

    class ScreenLogFormatter(logging.Formatter):
        """A custom formatter, adding colors."""

        LOG_FORMAT = r"%(name)25s - %(message)s // %(filename)s:%(lineno)d" if DEBUG else r"%(message)s"
        RESET_ANSI = "\x1b[0m"

        FORMATTERS = {
            logging.DEBUG: logging.Formatter(LOG_FORMAT + RESET_ANSI),
            logging.INFO: logging.Formatter(LOG_FORMAT + RESET_ANSI),
            logging.WARNING: logging.Formatter("\x1b[33;20m" + LOG_FORMAT + RESET_ANSI),
            logging.ERROR: logging.Formatter("\x1b[31;20m" + LOG_FORMAT + RESET_ANSI),
            logging.CRITICAL: logging.Formatter("\x1b[31;1m" + LOG_FORMAT + RESET_ANSI),
        }

        def format(self, record: logging.LogRecord) -> str:
            return self.FORMATTERS[record.levelno].format(record)

    logging.basicConfig()
    if filename:
        file_handler = logging.FileHandler(filename)
        file_handler.setFormatter(logging.Formatter(fmt=r"%(asctime)s [%(levelname)s] %(name)s :: %(message)s :: %(filename)s:%(lineno)d"))
        LogObjects.handlers.append(file_handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(ScreenLogFormatter())
    LogObjects.handlers.append(stream_handler)


def get_logger(name: str = "pypr", level: int | None = None) -> logging.Logger:
    """Return a named logger.

    Args:
        name (str): logger's name
        level (int): logger's level (auto if not set)
    """
    logger = logging.getLogger(name)
    if level is None:
        logger.setLevel(logging.DEBUG if DEBUG else logging.WARNING)
    else:
        logger.setLevel(level)
    logger.propagate = False
    for handler in LogObjects.handlers:
        logger.addHandler(handler)
    logger.info('Logger "%s" initialized', name)
    return logger


@dataclass
class SharedState:
    """Stores commonly requested properties."""

    active_workspace: str = ""  # workspace name
    active_monitor: str = ""  # monitor name
    active_window: str = ""  # window address
    variables: dict = field(default_factory=dict)
    monitors: list[str] = field(default_factory=list)
    hyprland_version: VersionInfo = field(default_factory=VersionInfo)


state: SharedState = SharedState()
"""
Exposes most-commonly accessed attributes to avoid specific IPC requests
- `active_monitor` monitor's name
- `active_workspace` workspace's name
- `active_window` window's address
"""


def prepare_for_quotes(text: str) -> str:
    """Escapes double quotes in text."""
    return text.replace('"', '\\"')


def apply_variables(template: str, variables: dict[str, str]) -> str:
    """Replace [var_name] with content from supplied variables.

    Args:
        template: the string template
        variables: a dict containing the variables to replace
    """
    pattern = r"\[([^\[\]]+)\]"

    def replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))

    return re.sub(pattern, replace, template)


def apply_filter(text: str, filt_cmd: str) -> str:
    """Apply filters to text.

    Currently supports only "s" command fom vim/ed
    """
    if not filt_cmd:
        return text
    if filt_cmd[0] == "s":  # vi-like substitute
        (_, base, replacement, opts) = filt_cmd.split(filt_cmd[1])
        return re.sub(base, replacement, text, count=0 if "g" in opts else 1)
    return text


class CastBoolMixin:
    """Adds `cast_bool` method."""

    log: logging.Logger

    def cast_bool(self, value: str | bool | None, default_value: bool = False) -> bool:
        """Recovers wrong typing on boolean values."""
        if isinstance(value, str):
            lv = value.lower().strip()
            r = lv not in {"false", "no", "off"}
            self.log.warning("Invalid value for boolean option: %s, considering it %s", value, r)
        return default_value if value is None else cast(bool, value)


def is_rotated(monitor: MonitorInfo) -> bool:
    """Return True if the monitor is rotated."""
    return monitor["transform"] in {1, 3, 5, 7}
