"""Debug mode state management."""

import os

__all__ = [
    "DEBUG",
    "is_debug",
    "set_debug",
]


class _DebugState:
    """Container for mutable debug state to avoid global statement."""

    value: bool = bool(os.environ.get("DEBUG"))


_debug_state = _DebugState()


def is_debug() -> bool:
    """Return the current debug state."""
    return _debug_state.value


def set_debug(value: bool) -> None:
    """Set the debug state."""
    _debug_state.value = value


# Backward compatible: DEBUG still works for reading initial state
# New code should use is_debug() for dynamic checks
DEBUG = bool(os.environ.get("DEBUG"))
