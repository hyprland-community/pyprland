"""Tests for the Niri backend adapter."""

import json
import logging

import pytest

from pyprland.common import SharedState
from pyprland.adapters.niri import NiriBackend, monitor_ids, niri_event_name, niri_output_to_monitor_info

LOG = logging.getLogger("test")

NIRI_WINDOW = {
    "id": 2,
    "title": "top",
    "app_id": "TermLog",
    "pid": 112511,
    "workspace_id": 5,
    "is_focused": False,
    "is_floating": True,
    "layout": {
        "pos_in_scrolling_layout": None,
        "tile_size": [600.0, 400.0],
        "window_size": [600, 400],
        "tile_pos_in_workspace_view": [100.0, 154.0],
        "window_offset_in_tile": [0.0, 0.0],
    },
}

NIRI_TILED_WINDOW = {
    "id": 4,
    "title": "editor",
    "app_id": "kitty",
    "pid": 112957,
    "workspace_id": 2,
    "is_floating": False,
    "layout": {
        "pos_in_scrolling_layout": [1, 1],
        "tile_size": [1912.0, 2116.0],
        "window_size": [1912, 2116],
        "tile_pos_in_workspace_view": None,
        "window_offset_in_tile": [0.0, 0.0],
    },
}


class FakeNiri(NiriBackend):
    """Niri backend with a recorded IPC layer."""

    def __init__(self, responses=None):  # noqa: D107
        super().__init__(SharedState())
        self.sent: list = []
        self.queries: list = []
        self.responses = responses or {}

    async def execute(self, command, *, log, **kwargs):  # noqa: D102
        self.sent.append(command)
        return True

    async def execute_json(self, command, *, log, **kwargs):  # noqa: D102
        if command == "clients":
            # Exercise the real translation, which re-enters via "windows".
            return await super().execute_json(command, log=log, **kwargs)
        self.queries.append(command)
        return self.responses[command]


def test_monitor_ids_are_stable_and_name_sorted():
    """Outputs get deterministic ids regardless of enumeration order."""
    assert monitor_ids(["HDMI-A-1", "DP-1"]) == {"DP-1": 0, "HDMI-A-1": 1}
    assert monitor_ids(["DP-1", "HDMI-A-1"]) == {"DP-1": 0, "HDMI-A-1": 1}


def test_monitor_info_carries_the_supplied_id():
    """niri_output_to_monitor_info no longer hardcodes id -1."""
    info = niri_output_to_monitor_info("DP-1", {"logical_size": {"width": 2560, "height": 1440}}, index=3)
    assert info["id"] == 3
    assert info["name"] == "DP-1"


@pytest.mark.asyncio
async def test_floating_window_exposes_real_geometry():
    """A floating window reports its pid, position, size and floating state."""
    backend = FakeNiri(
        {
            "windows": [NIRI_WINDOW],
            "workspaces": [{"id": 5, "output": "DP-1"}],
            "outputs": {"DP-1": {}, "HDMI-A-1": {}},
        }
    )
    (client,) = await backend.get_clients(log=LOG)

    assert client["pid"] == 112511
    assert client["floating"] is True
    assert client["at"] == (100, 154)
    assert client["size"] == (600, 400)
    assert client["monitor"] == 0


@pytest.mark.asyncio
async def test_tiled_window_without_position_falls_back_to_origin():
    """Tiled windows report a null position; it must not crash the mapping."""
    backend = FakeNiri(
        {
            "windows": [NIRI_TILED_WINDOW],
            "workspaces": [{"id": 2, "output": "HDMI-A-1"}],
            "outputs": {"DP-1": {}, "HDMI-A-1": {}},
        }
    )
    (client,) = await backend.get_clients(log=LOG)

    assert client["at"] == (0, 0)
    assert client["size"] == (1912, 2116)
    assert client["floating"] is False
    assert client["monitor"] == 1


@pytest.mark.asyncio
async def test_unreachable_workspaces_degrade_to_unknown_monitor():
    """Clients are still returned when the monitor mapping can't be resolved."""

    class Broken(FakeNiri):
        async def execute_json(self, command, *, log, **kwargs):
            if command == "windows":
                return [NIRI_WINDOW]
            raise ConnectionError

    (client,) = await Broken().get_clients(log=LOG)
    assert client["monitor"] == -1
    assert client["pid"] == 112511


@pytest.mark.asyncio
async def test_resize_window_sets_both_dimensions():
    """Niri needs one action per dimension, both using SetFixed."""
    backend = FakeNiri()
    assert await backend.resize_window("2", 600, 400, log=LOG)
    assert backend.sent == [
        {"Action": {"SetWindowWidth": {"id": 2, "change": {"SetFixed": 600}}}},
        {"Action": {"SetWindowHeight": {"id": 2, "change": {"SetFixed": 400}}}},
    ]


@pytest.mark.asyncio
async def test_move_window_targets_the_floating_layer():
    """Positions are absolute and sent as floats."""
    backend = FakeNiri()
    assert await backend.move_window("2", 100, 120, log=LOG)
    assert backend.sent == [{"Action": {"MoveFloatingWindow": {"id": 2, "x": {"SetFixed": 100.0}, "y": {"SetFixed": 120.0}}}}]


@pytest.mark.asyncio
async def test_floating_helpers():
    """Toggle is a toggle; set_window_floating is idempotent."""
    backend = FakeNiri()
    await backend.toggle_floating("2", log=LOG)
    await backend.set_window_floating("2", True, log=LOG)
    await backend.set_window_floating("2", False, log=LOG)
    assert backend.sent == [
        {"Action": {"ToggleWindowFloating": {"id": 2}}},
        {"Action": {"MoveWindowToFloating": {"id": 2}}},
        {"Action": {"MoveWindowToTiling": {"id": 2}}},
    ]


# ─── Event parsing ────────────────────────────────────────────────────────────


def test_event_names_follow_the_handler_convention():
    """Variants become snake_case `event_*` names the manager can look up."""
    assert niri_event_name("WorkspacesChanged") == "event_niri_workspaces_changed"
    assert niri_event_name("WindowOpenedOrChanged") == "event_niri_window_opened_or_changed"
    assert niri_event_name("ConfigLoaded") == "event_niri_config_loaded"


def test_parse_event_handles_the_real_niri_envelope():
    """Niri emits {"Variant": {...}} single-key objects, not a "Variant" key."""
    backend = FakeNiri()
    name, data = backend.parse_event('{"WindowFocusChanged": {"id": 3}}', log=LOG)
    assert name == "event_niri_window_focus_changed"
    assert data == {"id": 3}


@pytest.mark.parametrize(
    "raw",
    [
        "Started reading events.",  # non-JSON preamble
        '{"Ok": "Handled"}',  # a response, not an event
    ],
)
def test_parse_event_ignores_non_events(raw):
    """Noise on the socket must not be dispatched as an event."""
    assert FakeNiri().parse_event(raw, log=LOG) is None


# ─── Monitor mapping cache ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mapping_is_queried_once_then_cached():
    """Repeated get_clients calls must not re-query workspaces and outputs."""
    backend = FakeNiri(
        {
            "windows": [NIRI_WINDOW],
            "workspaces": [{"id": 5, "output": "DP-1"}],
            "outputs": {"DP-1": {}, "HDMI-A-1": {}},
        }
    )
    await backend.get_clients(log=LOG)
    await backend.get_clients(log=LOG)
    await backend.get_clients(log=LOG)

    assert backend.queries.count("workspaces") == 1
    assert backend.queries.count("outputs") == 1
    assert backend.queries.count("windows") == 3


@pytest.mark.asyncio
async def test_workspaces_changed_event_refreshes_mapping_without_ipc():
    """The event carries the full list, so no query is needed afterwards."""
    backend = FakeNiri({"windows": [NIRI_WINDOW], "outputs": {"DP-1": {}}})
    backend.parse_event('{"WorkspacesChanged": {"workspaces": [{"id": 5, "output": "DP-1"}]}}', log=LOG)

    (client,) = await backend.get_clients(log=LOG)

    assert client["monitor"] == 0
    assert "workspaces" not in backend.queries


@pytest.mark.asyncio
async def test_new_output_triggers_an_id_refresh():
    """A hotplugged output must not keep reporting an unknown monitor."""
    backend = FakeNiri(
        {
            "windows": [NIRI_WINDOW],
            "workspaces": [{"id": 5, "output": "DP-1"}],
            "outputs": {"DP-1": {}},
        }
    )
    await backend.get_clients(log=LOG)
    assert backend.queries.count("outputs") == 1

    # A new monitor appears, carrying the window's workspace with it.
    backend.responses["outputs"] = {"DP-1": {}, "DP-2": {}}
    backend.parse_event('{"WorkspacesChanged": {"workspaces": [{"id": 5, "output": "DP-2"}]}}', log=LOG)
    (client,) = await backend.get_clients(log=LOG)

    assert backend.queries.count("outputs") == 2
    assert client["monitor"] == 1


@pytest.mark.asyncio
async def test_config_reload_invalidates_output_ids():
    """Outputs may be reconfigured, so their ids must be re-resolved."""
    backend = FakeNiri(
        {
            "windows": [NIRI_WINDOW],
            "workspaces": [{"id": 5, "output": "DP-1"}],
            "outputs": {"DP-1": {}},
        }
    )
    await backend.get_clients(log=LOG)
    backend.parse_event('{"ConfigLoaded": {"failed": false}}', log=LOG)
    await backend.get_clients(log=LOG)

    assert backend.queries.count("outputs") == 2


# ─── Synthesised events ───────────────────────────────────────────────────────


def _window(wid, floating=False, title="t"):
    return {"id": wid, "title": title, "app_id": "kitty", "is_floating": floating}


def _opened_or_changed(backend, wid, floating=False, title="t"):
    raw = json.dumps({"WindowOpenedOrChanged": {"window": _window(wid, floating, title)}})
    return [name for name, _ in backend.parse_events(raw, log=LOG)]


def test_raw_event_is_always_dispatched():
    """Synthesis adds events, it never replaces the original."""
    backend = FakeNiri()
    names = _opened_or_changed(backend, 1)
    assert names[0] == "event_niri_window_opened_or_changed"


def test_window_open_fires_once_despite_repeated_events():
    """Niri re-sends WindowOpenedOrChanged on title changes; open must not repeat."""
    backend = FakeNiri()
    first = _opened_or_changed(backend, 16, title="kitty")
    second = _opened_or_changed(backend, 16, title="sleep")

    assert "event_niri_window_opened" in first
    assert "event_niri_window_opened" not in second


def test_floating_change_is_derived_from_the_flipped_flag():
    """Niri has no floating event, so it comes from diffing is_floating."""
    backend = FakeNiri()
    _opened_or_changed(backend, 2, floating=False)

    assert "event_niri_window_floating_changed" in _opened_or_changed(backend, 2, floating=True)
    # A further event with no change must stay quiet.
    assert "event_niri_window_floating_changed" not in _opened_or_changed(backend, 2, floating=True)
    assert "event_niri_window_floating_changed" in _opened_or_changed(backend, 2, floating=False)


def test_reopened_id_is_an_open_again():
    """A closed window frees its id, so a later sighting is a fresh open."""
    backend = FakeNiri()
    _opened_or_changed(backend, 16)
    backend.parse_events('{"WindowClosed": {"id": 16}}', log=LOG)

    assert "event_niri_window_opened" in _opened_or_changed(backend, 16)


def test_windows_changed_rebuilds_without_reporting_opens():
    """The full-replacement snapshot is state, not a burst of openings."""
    backend = FakeNiri()
    raw = json.dumps({"WindowsChanged": {"windows": [_window(1), _window(2, floating=True)]}})
    names = [name for name, _ in backend.parse_events(raw, log=LOG)]

    assert names == ["event_niri_windows_changed"]
    # ...but the state is now known, so no spurious "opened" follows.
    assert "event_niri_window_opened" not in _opened_or_changed(backend, 2, floating=True)


def _workspaces_changed(backend, *outputs):
    raw = json.dumps({"WorkspacesChanged": {"workspaces": [{"id": i, "output": o} for i, o in enumerate(outputs)]}})
    return backend.parse_events(raw, log=LOG)


def test_first_workspace_snapshot_is_not_a_monitor_change():
    """Connecting to the stream must not look like every monitor being added."""
    backend = FakeNiri()
    names = [name for name, _ in _workspaces_changed(backend, "DP-1", "HDMI-A-1")]
    assert names == ["event_niri_workspaces_changed"]


def test_monitor_add_and_remove_are_derived_from_workspaces():
    """Niri has no monitor event; the output set diff stands in for one."""
    backend = FakeNiri()
    _workspaces_changed(backend, "DP-1", "HDMI-A-1")

    events = _workspaces_changed(backend, "DP-1", "DP-2")
    assert events[1:] == [
        ("event_niri_monitor_added", {"output": "DP-2"}),
        ("event_niri_monitor_removed", {"output": "HDMI-A-1"}),
    ]


def test_unchanged_outputs_emit_no_monitor_events():
    """Workspace churn on the same monitors is not a monitor change."""
    backend = FakeNiri()
    _workspaces_changed(backend, "DP-1")
    names = [name for name, _ in _workspaces_changed(backend, "DP-1")]
    assert names == ["event_niri_workspaces_changed"]


# ─── Address handling ─────────────────────────────────────────────────────────


def test_niri_addresses_have_no_prefix():
    """Niri window ids are plain integers; the 0x dance must not mangle them."""
    backend = FakeNiri()
    assert backend.short_address("15") == "15"
    assert backend.full_address("15") == "15"
    # Short ids are valid in niri, unlike Hyprland's long pointers.
    assert backend.full_address("2") == "2"
    assert backend.full_address("") == ""


def test_hyprland_addresses_round_trip():
    """The default backend behaviour still strips and restores the prefix."""
    from pyprland.adapters.hyprland import HyprlandBackend

    backend = HyprlandBackend(SharedState())
    assert backend.short_address("0x5581abcd") == "5581abcd"
    assert backend.full_address("5581abcd") == "0x5581abcd"
    assert backend.full_address("0x5581abcd") == "0x5581abcd"
    # Too short to be a real address.
    assert backend.full_address("12") == ""


# ─── Batch window operations ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_move_windows_issues_one_request_per_window():
    """Niri has no batch protocol, so the batch is unrolled."""
    backend = FakeNiri()
    assert await backend.move_windows([("2", 10, 20), ("3", 30, 40)], log=LOG)
    assert backend.sent == [
        {"Action": {"MoveFloatingWindow": {"id": 2, "x": {"SetFixed": 10.0}, "y": {"SetFixed": 20.0}}}},
        {"Action": {"MoveFloatingWindow": {"id": 3, "x": {"SetFixed": 30.0}, "y": {"SetFixed": 40.0}}}},
    ]


@pytest.mark.asyncio
async def test_move_windows_to_workspace_unrolls_too():
    """Each window is re-parented individually."""
    backend = FakeNiri()
    await backend.move_windows_to_workspace(["2", "3"], "7", log=LOG)
    assert backend.sent == [
        {"Action": {"MoveWindowToWorkspace": {"window_id": 2, "reference": {"Id": 7}, "focus": False}}},
        {"Action": {"MoveWindowToWorkspace": {"window_id": 3, "reference": {"Id": 7}, "focus": False}}},
    ]


@pytest.mark.asyncio
async def test_move_workspace_to_monitor_accepts_ids_and_names():
    """Niri references a workspace by id or by name, never by index here."""
    backend = FakeNiri()
    await backend.move_workspace_to_monitor("9", "DP-1", log=LOG)
    await backend.move_workspace_to_monitor("special:term", "DP-1", log=LOG)
    assert backend.sent == [
        {"Action": {"MoveWorkspaceToMonitor": {"reference": {"Id": 9}, "output": "DP-1"}}},
        {"Action": {"MoveWorkspaceToMonitor": {"reference": {"Name": "special:term"}, "output": "DP-1"}}},
    ]


@pytest.mark.asyncio
async def test_unsupported_batch_operations_are_reported_not_faked():
    """Niri can't do these; they must return False rather than pretend."""
    backend = FakeNiri()
    assert await backend.raise_windows(["2"], log=LOG) is False
    assert await backend.set_window_animations(["2"], enabled=False, log=LOG) is False
    assert await backend.set_keyword("general:gaps_out 10", log=LOG) is False
    assert backend.sent == []


# ─── Scratchpad parking workspaces ────────────────────────────────────────────


def test_niri_parks_scratchpads_on_a_named_workspace():
    """Niri has no special workspaces, so a plain named one is used."""
    backend = FakeNiri()
    assert backend.scratch_workspace("term") == "pypr-S-term"
    # Characters that are illegal in a workspace name are escaped.
    assert backend.scratch_workspace("my term:1") == "pypr-S-my_term_1"


def test_only_pyprland_workspaces_count_as_hidden_on_niri():
    """Niri users may legitimately name a workspace anything else."""
    backend = FakeNiri()
    assert backend.is_hidden_workspace("pypr-S-term") is True
    assert backend.is_hidden_workspace("special:whatever") is False
    assert backend.is_hidden_workspace("3") is False


def test_hyprland_still_treats_every_special_workspace_as_hidden():
    """The narrower Niri rule must not leak into the Hyprland behaviour."""
    from pyprland.adapters.hyprland import HyprlandBackend

    backend = HyprlandBackend(SharedState())
    assert backend.scratch_workspace("term") == "special:S-term"
    assert backend.is_hidden_workspace("special:magic") is True
    assert backend.is_scratch_workspace("special:magic") is False
    assert backend.is_scratch_workspace("special:S-term") is True


@pytest.mark.asyncio
async def test_undeclared_parking_workspaces_are_reported():
    """Niri ignores moves to undeclared names, so they must be caught early."""
    backend = FakeNiri({"workspaces": [{"id": 1, "name": "pypr-S-term"}, {"id": 2, "name": None}]})
    assert await backend.missing_scratch_workspaces(["term", "btop"], log=LOG) == ["pypr-S-btop"]


@pytest.mark.asyncio
async def test_hyprland_never_reports_missing_workspaces():
    """They're created on demand there, so the check is a no-op."""
    from pyprland.adapters.hyprland import HyprlandBackend

    backend = HyprlandBackend(SharedState())
    assert backend.scratch_workspaces_are_implicit is True
    assert await backend.missing_scratch_workspaces(["term"], log=LOG) == []


@pytest.mark.asyncio
async def test_monitors_carry_their_active_workspace():
    """Without this the show path would move windows to an empty workspace."""
    backend = FakeNiri(
        {
            "outputs": {"DP-1": {"logical_size": {"width": 2560, "height": 1440}}},
            "workspaces": [
                {"id": 5, "output": "DP-1", "is_active": True},
                {"id": 9, "output": "DP-1", "is_active": False},
            ],
        }
    )
    (monitor,) = await backend.get_monitors(log=LOG)
    assert monitor["activeWorkspace"] == {"id": 5, "name": "5"}


@pytest.mark.asyncio
async def test_named_active_workspace_keeps_its_name():
    """A user-named workspace reports its name rather than its id."""
    backend = FakeNiri(
        {
            "outputs": {"DP-1": {}},
            "workspaces": [{"id": 5, "output": "DP-1", "is_active": True, "name": "web"}],
        }
    )
    (monitor,) = await backend.get_monitors(log=LOG)
    assert monitor["activeWorkspace"] == {"id": 5, "name": "web"}


# ─── Window rules ─────────────────────────────────────────────────────────────


def test_niri_cannot_declare_window_rules():
    """No runtime config mutation, so rules must be applied reactively."""
    assert FakeNiri().supports_window_rules is False


def test_hyprland_declares_window_rules():
    """The capability must stay on for the backend that has it."""
    from pyprland.adapters.hyprland import HyprlandBackend

    assert HyprlandBackend(SharedState()).supports_window_rules is True


@pytest.mark.asyncio
async def test_monitor_list_order_matches_monitor_ids():
    """Indexing the list positionally must agree with the reported ids."""
    backend = FakeNiri(
        {
            # Deliberately not in sorted order.
            "outputs": {"HDMI-A-1": {}, "DP-1": {}},
            "workspaces": [],
        }
    )
    monitors = await backend.get_monitors(log=LOG)
    assert [m["name"] for m in monitors] == ["DP-1", "HDMI-A-1"]
    assert [m["id"] for m in monitors] == [0, 1]


# ─── Output parsing (regressions found against a live compositor) ─────────────

REAL_OUTPUT = {
    "name": "DP-1",
    "make": "Dell",
    "model": "U3415W",
    # Niri marks the active mode with this index, NOT an `is_active` flag.
    "current_mode": 1,
    "modes": [
        {"width": 1920, "height": 1080, "refresh_rate": 60000, "is_preferred": False},
        {"width": 3440, "height": 1440, "refresh_rate": 59999, "is_preferred": True},
    ],
    # The field is `logical`, not `logical_size`/`logical_position`.
    "logical": {"x": 3840, "y": 0, "width": 3440, "height": 1440, "scale": 1.0, "transform": "Normal"},
}


def test_output_resolution_comes_from_the_current_mode_index():
    """Niri modes have no is_active flag; reading one yielded 0x0 monitors."""
    info = niri_output_to_monitor_info("DP-1", REAL_OUTPUT, index=0)
    assert (info["width"], info["height"]) == (3440, 1440)
    assert info["refreshRate"] == pytest.approx(59.999)
    assert (info["x"], info["y"]) == (3840, 0)
    assert info["scale"] == 1.0
    assert info["description"] == "Dell U3415W"


def test_output_falls_back_to_the_logical_size():
    """Without modes, the logical size scaled back up is the best estimate."""
    info = niri_output_to_monitor_info(
        "DP-2",
        {"logical": {"x": 0, "y": 0, "width": 1280, "height": 720, "scale": 2.0, "transform": "Normal"}},
    )
    assert (info["width"], info["height"]) == (2560, 1440)


@pytest.mark.asyncio
async def test_focused_monitor_is_derived_from_the_focused_workspace():
    """Niri outputs carry no focus flag, so get_monitor_props found nothing."""
    backend = FakeNiri(
        {
            "outputs": {"DP-1": REAL_OUTPUT, "HDMI-A-1": {}},
            "workspaces": [
                {"id": 5, "output": "DP-1", "is_active": True, "is_focused": True},
                {"id": 2, "output": "HDMI-A-1", "is_active": True, "is_focused": False},
            ],
        }
    )
    focused = await backend.get_monitor_props(log=LOG)
    assert focused["name"] == "DP-1"


@pytest.mark.asyncio
async def test_clients_request_is_served_in_the_hyprland_shape():
    """Plugins ask for "clients"; Niri has no such variant."""
    backend = FakeNiri(
        {
            "windows": [NIRI_WINDOW],
            "workspaces": [{"id": 5, "output": "DP-1"}],
            "outputs": {"DP-1": {}},
        }
    )
    clients = await backend.execute_json("clients", log=LOG)
    assert clients[0]["address"] == "2"
    assert clients[0]["pid"] == 112511
    assert "Clients" not in backend.queries


# ─── Floating window placement ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_move_window_translates_global_coordinates_to_the_output():
    """Niri positions floating windows relative to their own output.

    Callers work in Hyprland's global space, so anything on a secondary
    monitor used to be pushed past the right edge and clamped back.
    """
    backend = FakeNiri(
        {
            "windows": [{"id": 7, "workspace_id": 5}],
            "workspaces": [{"id": 5, "output": "DP-1"}],
            "outputs": {"DP-1": {"logical": {"x": 3840, "y": 0}}},
        }
    )
    await backend.move_window("7", 4600, 94, log=LOG)
    assert backend.sent == [{"Action": {"MoveFloatingWindow": {"id": 7, "x": {"SetFixed": 760.0}, "y": {"SetFixed": 94.0}}}}]


@pytest.mark.asyncio
async def test_move_window_falls_back_to_the_global_position():
    """An unknown window must still be moved rather than silently dropped."""
    backend = FakeNiri({"windows": [], "workspaces": [], "outputs": {}})
    await backend.move_window("7", 120, 40, log=LOG)
    assert backend.sent[0]["Action"]["MoveFloatingWindow"]["x"] == {"SetFixed": 120.0}


def test_niri_cannot_park_windows_offscreen():
    """Niri clamps floating windows on-screen, so the slide-in is skipped."""
    assert NiriBackend.supports_offscreen_placement is False
