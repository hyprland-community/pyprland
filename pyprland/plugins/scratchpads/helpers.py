"""Helper functions for the scratchpads plugin."""

__all__ = [
    "DynMonitorConfig",
    "get_active_space_identifier",
    "get_all_space_identifiers",
    "get_match_fn",
    "get_size",
    "compute_offset",
    "apply_offset",
]

import logging
import re
from collections.abc import Callable
from typing import Any

from ...common import SharedState, is_rotated
from ...types import MonitorInfo


def mk_scratch_name(uid: str) -> str:
    """Return scratchpad name as register in Hyprland.

    Args:
        uid: Unique identifier for the scratchpad
    """
    escaped = uid.replace(":", "_").replace("/", "_").replace(" ", "_")
    return f"special:S-{escaped}"


def compute_offset(pos1: tuple[int, int], pos2: tuple[int, int]) -> tuple[int, int]:
    """Compute the offset between two positions.

    Args:
        pos1: First position (x, y)
        pos2: Second position (x, y)
    """
    if pos1 is None or pos2 is None:
        return (0, 0)
    return pos1[0] - pos2[0], pos1[1] - pos2[1]


def apply_offset(pos: tuple[int, int], offset: tuple[int, int]) -> tuple[int, int]:
    """Apply the offset to the position.

    Args:
        pos: Base position (x, y)
        offset: Offset to apply (dx, dy)
    """
    return pos[0] + offset[0], pos[1] + offset[1]


def get_size(monitor: MonitorInfo) -> tuple[int, int]:
    """Get the (width, height) size of the monitor.

    Args:
        monitor: Monitor information
    """
    s = monitor["scale"]
    h, w = int(monitor["height"] / s), int(monitor["width"] / s)
    if is_rotated(monitor):
        return (h, w)
    return (w, h)


def get_active_space_identifier(state: SharedState) -> tuple[str, str]:
    """Return a unique object for the workspace + monitor combination.

    Args:
        state: Shared state containing active workspace and monitor
    """
    return (state.active_workspace, state.active_monitor)


async def get_all_space_identifiers(monitors: list[MonitorInfo]) -> list[tuple[str, str]]:
    """Return a list of every space identifiers (workspace + monitor) on active screens.

    Args:
        monitors: List of active monitors
    """
    return [(monitor["activeWorkspace"]["name"], monitor["name"]) for monitor in monitors]


_match_fn_re_cache = {}


def get_match_fn(prop_name: str, prop_value: float | bool | str | list) -> Callable[[Any, Any], bool]:
    """Return a function to match a client based on a property.

    Args:
        prop_name: Name of the property to match
        prop_value: Value to match against (can be regex starting with "re:")
    """
    assert prop_name  # may be used for more specific matching
    if isinstance(prop_value, str) and prop_value.startswith("re:"):
        # get regex from cache if possible:
        if prop_value not in _match_fn_re_cache:
            regex = re.compile(prop_value[3:])

            def _comp_function(value1: str, _value2: str) -> bool:
                return bool(regex.match(value1))

            _match_fn_re_cache[prop_value] = _comp_function
        return _match_fn_re_cache[prop_value]
    return lambda value1, value2: value1 == value2


class DynMonitorConfig:
    """A `dict`-like object allowing per-monitor overrides."""

    def __init__(
        self,
        ref: dict[str, float | bool | list | str],
        monitor_override: dict[str, dict[str, float | bool | list | str]],
        state: SharedState,
        log: logging.Logger,
    ) -> None:
        """Initialize dynamic configuration.

        Args:
            ref: Reference configuration
            monitor_override: Monitor-specific overrides
            state: Shared state
            log: Logger instance
        """
        self.ref = ref
        self.mon_override = monitor_override
        self.state = state
        self.log = log

    def __setitem__(self, name: str, value: float | bool | str | list) -> None:
        self.ref[name] = value

    def update(self, other: dict[str, float | bool | str | list]) -> None:
        """Update the configuration with another dictionary.

        Args:
            other: Dictionary to update from
        """
        self.ref.update(other)

    def __getitem__(self, name: str) -> float | bool | str | list:
        override = self.mon_override.get(self.state.active_monitor, {})
        if name in override:
            return override[name]
        return self.ref[name]

    def __contains__(self, name: object) -> bool:
        assert isinstance(name, str)
        try:
            self[name]  # pylint: disable=pointless-statement
        except KeyError:
            return False
        return True

    def get(self, name: str, default: object = None) -> object | None:
        """Get the attribute `name`.

        Args:
            name: Attribute name
            default: Default value if not found
        """
        try:
            return self[name]
        except KeyError:
            return default

    def get_bool(self, name: str, default: bool = False) -> bool:
        """Get a boolean value, handling loose typing.

        Args:
            name: Attribute name
            default: Default value if not found
        """
        value = self.get(name)
        if isinstance(value, str):
            lv = value.lower().strip()
            return lv not in {"false", "no", "off", "0"}
        if value is None:
            return default
        return bool(value)

    def get_int(self, name: str, default: int = 0) -> int:
        """Get an integer value.

        Args:
            name: Attribute name
            default: Default value if not found or invalid
        """
        value = self.get(name)
        if value is None:
            return default
        try:
            return int(value)  # type: ignore
        except (ValueError, TypeError):
            self.log.warning("Invalid integer value for %s: %s", name, value)
            return default

    def get_float(self, name: str, default: float = 0.0) -> float:
        """Get a float value.

        Args:
            name: Attribute name
            default: Default value if not found or invalid
        """
        value = self.get(name)
        if value is None:
            return default
        try:
            return float(value)  # type: ignore
        except (ValueError, TypeError):
            self.log.warning("Invalid float value for %s: %s", name, value)
            return default

    def get_str(self, name: str, default: str = "") -> str:
        """Get a string value.

        Args:
            name: Attribute name
            default: Default value if not found
        """
        value = self.get(name)
        if value is None:
            return default
        return str(value)

    def __str__(self) -> str:
        return f"{self.ref} {self.mon_override}"
