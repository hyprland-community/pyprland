"""Tests for the Niri event handlers of the scratchpads plugin.

These cover the translation layer only: that each `event_niri_*` handler
normalises Niri's structured payload into the same arguments the Hyprland
handler produces for the shared `_on_*` core.
"""

import logging
from unittest.mock import AsyncMock

import pytest

from pyprland.adapters.hyprland import HyprlandBackend
from pyprland.adapters.niri import NiriBackend
from pyprland.common import SharedState
from pyprland.plugins.scratchpads.events import EventsMixin


class Harness(EventsMixin):
    """EventsMixin with the shared cores and backend stubbed out."""

    def __init__(self, backend):
        self.log = logging.getLogger("test")
        self.backend = backend
        self.scratches = {}
        self.on_reload = AsyncMock()
        for core in (
            "_on_floating_changed",
            "_on_workspace_changed",
            "_on_window_closed",
            "_on_monitor_added",
            "_on_monitor_removed",
            "_on_focus_changed",
            "_on_window_opened",
        ):
            setattr(self, core, AsyncMock())


@pytest.fixture
def niri():
    return Harness(NiriBackend(SharedState()))


@pytest.fixture
def hyprland():
    return Harness(HyprlandBackend(SharedState()))


@pytest.mark.asyncio
async def test_config_loaded_reloads(niri):
    """A successful Niri config load behaves like Hyprland's reload."""
    await niri.event_niri_config_loaded({"failed": False})
    niri.on_reload.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_config_load_does_not_reload(niri):
    """Niri reports failed loads too; reconfiguring on those would be wrong."""
    await niri.event_niri_config_loaded({"failed": True})
    niri.on_reload.assert_not_awaited()


@pytest.mark.asyncio
async def test_floating_change_matches_hyprland_arguments(niri, hyprland):
    """Both compositors reach the core with an unprefixed address and a bool."""
    await niri.event_niri_window_floating_changed({"id": 15, "is_floating": True})
    niri._on_floating_changed.assert_awaited_once_with("15", True)

    await hyprland.event_changefloatingmode("5581abcd,1")
    hyprland._on_floating_changed.assert_awaited_once_with("5581abcd", True)


@pytest.mark.asyncio
async def test_only_the_focused_workspace_counts(niri):
    """Niri activates a workspace per output; only the focused one maps over."""
    await niri.event_niri_workspace_activated({"id": 7, "focused": False})
    niri._on_workspace_changed.assert_not_awaited()

    await niri.event_niri_workspace_activated({"id": 7, "focused": True})
    niri._on_workspace_changed.assert_awaited_once_with("7")


@pytest.mark.asyncio
async def test_closed_window_reaches_core_with_a_full_address(niri, hyprland):
    """Addresses are normalised per backend, not with a hardcoded prefix."""
    await niri.event_niri_window_closed({"id": 15})
    niri._on_window_closed.assert_awaited_once_with("15")

    await hyprland.event_closewindow("5581abcd")
    hyprland._on_window_closed.assert_awaited_once_with("0x5581abcd")


@pytest.mark.asyncio
async def test_focus_change_handles_a_null_window(niri):
    """Niri reports no focused window as null; Hyprland has no equivalent."""
    await niri.event_niri_window_focus_changed({"id": None})
    niri._on_focus_changed.assert_awaited_once_with("")

    niri._on_focus_changed.reset_mock()
    await niri.event_niri_window_focus_changed({"id": 15})
    niri._on_focus_changed.assert_awaited_once_with("15")


@pytest.mark.asyncio
async def test_window_opened_passes_the_bare_id(niri, hyprland):
    """The core keys the registry by unprefixed address in both cases."""
    await niri.event_niri_window_opened({"id": 15, "app_id": "kitty"})
    niri._on_window_opened.assert_awaited_once_with("15")

    await hyprland.event_openwindow("5581abcd,1,kitty,title")
    hyprland._on_window_opened.assert_awaited_once_with("5581abcd")


@pytest.mark.asyncio
async def test_synthesised_monitor_events_unwrap_the_output_name(niri):
    """The backend synthesises these; handlers just unwrap the payload."""
    await niri.event_niri_monitor_added({"output": "DP-2"})
    niri._on_monitor_added.assert_awaited_once_with("DP-2")

    await niri.event_niri_monitor_removed({"output": "HDMI-A-1"})
    niri._on_monitor_removed.assert_awaited_once_with("HDMI-A-1")
