"""Helper functions for the scratchpads plugin."""

__all__ = [
    "OverridableConfig",
    "get_active_space_identifier",
    "get_all_space_identifiers",
    "get_match_fn",
]

import re
from collections.abc import Callable
from typing import Any

from ...common import state
from ...types import MonitorInfo


def get_active_space_identifier() -> tuple[str, str]:
    """Return a unique object for the workspace + monitor combination."""
    return (state.active_workspace, state.active_monitor)


async def get_all_space_identifiers(monitors: list[MonitorInfo]) -> list[tuple[str, str]]:
    """Return a list of every space identifiers (workspace + monitor) on active screens."""
    return [(monitor["activeWorkspace"]["name"], monitor["name"]) for monitor in monitors]


_match_fn_re_cache = {}


def get_match_fn(prop_name: str, prop_value: float | bool | str | list) -> Callable[[Any, Any], bool]:
    """Return a function to match a client based on a property."""
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


class OverridableConfig(dict):
    """A `dict`-like object allowing per-monitor overrides."""

    def __init__(
        self, ref: dict[str, float | bool | list | str], monitor_override: dict[str, dict[str, float | bool | list | str]]
    ) -> None:
        self.ref = ref
        self.mon_override = monitor_override

    def __setitem__(self, name: str, value: float | bool | str | list) -> None:
        self.ref[name] = value

    def __getitem__(self, name: str) -> float | bool | str | list:
        override = self.mon_override.get(state.active_monitor, {})
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
        """Get the attribute `name`."""
        try:
            return self[name]
        except KeyError:
            return default

    def __str__(self) -> str:
        return f"{self.ref} {self.mon_override}"
