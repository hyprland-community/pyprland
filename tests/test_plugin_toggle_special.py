import pytest
from unittest.mock import Mock, AsyncMock
from pyprland.plugins.toggle_special import Extension
from pyprland.common import state


@pytest.fixture
def extension():
    state.active_workspace = "1"

    ext = Extension("toggle_special")
    ext.hyprctl = AsyncMock()
    ext.hyprctl_json = AsyncMock()
    return ext


@pytest.mark.asyncio
async def test_run_toggle_special_minimize(extension):
    # Current window is in a normal workspace (id >= 1)
    # Should move to special workspace
    extension.hyprctl_json.return_value = {"address": "0x123", "workspace": {"id": 1}}

    await extension.run_toggle_special("minimized")

    extension.hyprctl.assert_called_with("movetoworkspacesilent special:minimized,address:0x123")


@pytest.mark.asyncio
async def test_run_toggle_special_restore(extension):
    # Current window is in a special workspace (id < 1)
    # Should toggle special workspace, move back to active, and focus
    extension.hyprctl_json.return_value = {"address": "0x123", "workspace": {"id": -99}}

    await extension.run_toggle_special("minimized")

    expected_calls = [
        "togglespecialworkspace minimized",
        f"movetoworkspacesilent {state.active_workspace},address:0x123",
        "focuswindow address:0x123",
    ]

    extension.hyprctl.assert_called_with(expected_calls)
