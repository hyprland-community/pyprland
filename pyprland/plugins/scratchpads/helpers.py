"Helper functions for the scratchpads plugin"

__all__ = [
    "get_active_space_identifier",
    "get_all_space_identifiers",
    "get_match_fn",
    "OverridableConfig",
]

import re

from ...common import state


def get_active_space_identifier():
    "Returns a unique object for the workspace + monitor combination"
    return (state.active_workspace, state.active_monitor)


async def get_all_space_identifiers(monitors):
    "Returns a list of every space identifiers (workspace + monitor) on active screens"
    return [
        (monitor["activeWorkspace"]["name"], monitor["name"]) for monitor in monitors
    ]


_match_fn_re_cache = {}


def get_match_fn(prop_name, prop_value):
    "Returns a function to match a client based on a property"
    assert prop_name  # may be used for more specific matching
    if isinstance(prop_value, str) and prop_value.startswith("re:"):
        # get regex from cache if possible:
        if prop_value not in _match_fn_re_cache:
            regex = re.compile(prop_value[3:])
            _match_fn_re_cache[prop_value] = lambda value1, value2: regex.match(value1)
        return _match_fn_re_cache[prop_value]
    return lambda value1, value2: value1 == value2


class OverridableConfig:
    "A `dict`-like object allowing per-monitor overrides"

    def __init__(self, ref, monitor_override):
        self.ref = ref
        self.mon_override = monitor_override

    def __setitem__(self, name, value):
        self.ref[name] = value

    def __getitem__(self, name):
        override = self.mon_override.get(state.active_monitor, {})
        if name in override:
            return override[name]
        return self.ref[name]

    def __contains__(self, name):
        try:
            self[name]  # pylint: disable=pointless-statement
            return True
        except KeyError:
            return False

    def get(self, name, default=None):
        "get the attribute `name`"
        try:
            return self[name]
        except KeyError:
            return default

    def __str__(self):
        return f"{self.ref} {self.mon_override}"
