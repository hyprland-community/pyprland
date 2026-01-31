"""Helper functions for the scratchpads plugin."""

__all__ = [
    "DynMonitorConfig",
    "apply_offset",
    "compute_offset",
    "get_active_space_identifier",
    "get_all_space_identifiers",
    "get_match_fn",
    "get_size",
]

import logging
import re
from collections.abc import Callable
from typing import Any

from ...common import SharedState, is_rotated
from ...config import ConfigValueType, SchemaAwareMixin
from ...models import MonitorInfo
from ...validation import ConfigItems


def mk_scratch_name(uid: str) -> str:
    """Return scratchpad name as register in Hyprland.

    Args:
        uid: Unique identifier for the scratchpad
    """
    escaped = uid.replace(":", "_").replace("/", "_").replace(" ", "_")
    return f"special:S-{escaped}"


def compute_offset(pos1: tuple[int, int] | None, pos2: tuple[int, int] | None) -> tuple[int, int]:
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


_match_fn_re_cache: dict[str, Callable[[Any, Any], bool]] = {}


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


class DynMonitorConfig(SchemaAwareMixin):
    """A `dict`-like object allowing per-monitor overrides with schema-aware defaults."""

    def __init__(
        self,
        ref: dict[str, ConfigValueType],
        monitor_override: dict[str, dict[str, ConfigValueType]],
        state: SharedState,
        *,
        log: logging.Logger,
        schema: ConfigItems | None = None,
    ) -> None:
        """Initialize dynamic configuration.

        Args:
            ref: Reference configuration
            monitor_override: Monitor-specific overrides
            state: Shared state
            log: Logger instance
            schema: Optional schema for default value lookups
        """
        self.__init_schema__()
        self.ref = ref
        self.mon_override = monitor_override
        self.state = state
        self.log = log
        if schema:
            self.set_schema(schema)

    def __setitem__(self, name: str, value: ConfigValueType) -> None:
        self.ref[name] = value

    def update(self, other: dict[str, ConfigValueType]) -> None:
        """Update the configuration with another dictionary.

        Args:
            other: Dictionary to update from
        """
        self.ref.update(other)

    def _get_raw(self, name: str) -> ConfigValueType:
        """Get raw value from ref or monitor override. Raises KeyError if not found."""
        override = self.mon_override.get(self.state.active_monitor, {})
        if name in override:
            return override[name]
        if name in self.ref:
            return self.ref[name]
        raise KeyError(name)

    def __getitem__(self, name: str) -> ConfigValueType:
        """Get value, checking monitor override first, then ref. Raises KeyError if not found."""
        return self._get_raw(name)

    def __contains__(self, name: object) -> bool:
        """Check if name is explicitly set (not from schema defaults)."""
        assert isinstance(name, str)
        return self.has_explicit(name)

    def __str__(self) -> str:
        return f"{self.ref} {self.mon_override}"
