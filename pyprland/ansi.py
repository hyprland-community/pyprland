"""ANSI terminal color utilities.

Provides constants and helpers for terminal coloring with proper
NO_COLOR environment variable support and TTY detection.
"""

import os
import sys
from typing import TextIO

__all__ = [
    "BLACK",
    "BOLD",
    "DIM",
    "RED",
    "RESET",
    "YELLOW",
    "HandlerStyles",
    "LogStyles",
    "colorize",
    "make_style",
    "should_colorize",
]

# ANSI escape sequence prefix
_ESC = "\x1b["

# Reset all attributes
RESET = f"{_ESC}0m"

# Style codes
BOLD = "1"
DIM = "2"

# Foreground color codes
BLACK = "30"
RED = "31"
YELLOW = "33"


def should_colorize(stream: TextIO | None = None) -> bool:
    """Determine if ANSI colors should be used for the given stream.

    Respects:
    - NO_COLOR environment variable (disables colors)
    - FORCE_COLOR environment variable (forces colors)
    - TTY detection (disables colors when piping)

    Args:
        stream: The output stream to check. Defaults to sys.stderr.

    Returns:
        True if colors should be used, False otherwise.
    """
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    if stream is None:
        stream = sys.stderr
    return hasattr(stream, "isatty") and stream.isatty()


def colorize(text: str, *codes: str) -> str:
    """Wrap text in ANSI color codes.

    Args:
        text: The text to colorize.
        *codes: ANSI codes to apply (e.g., RED, BOLD).

    Returns:
        The text wrapped in ANSI escape sequences.
    """
    if not codes:
        return text
    return f"{_ESC}{';'.join(codes)}m{text}{RESET}"


def make_style(*codes: str) -> tuple[str, str]:
    """Create a style prefix and suffix pair.

    Args:
        *codes: ANSI codes to apply.

    Returns:
        Tuple of (prefix, suffix) strings for use in formatters.
    """
    if not codes:
        return ("", RESET)
    return (f"{_ESC}{';'.join(codes)}m", RESET)


class LogStyles:
    """Pre-built styles for log levels."""

    WARNING = (YELLOW, DIM)
    ERROR = (RED, DIM)
    CRITICAL = (RED, BOLD)


class HandlerStyles:
    """Pre-built styles for handler logging."""

    COMMAND = (YELLOW, BOLD)  # run_* methods
    EVENT = (BLACK, BOLD)  # event_* methods
