import pytest
from unittest.mock import Mock, AsyncMock
from pyprland.plugins.toggle_special import Extension
from pyprland.common import SharedState


@pytest.fixture
def extension():
    ext = Extension("toggle_special")
    ext.state = SharedState()
    ext.state.active_workspace = "1"

    ext.backend = AsyncMock()
    return ext


@pytest.mark.asyncio
async def test_run_toggle_special_minimize(extension):
    # Current window is in a normal workspace (id >= 1)
    # Should move to special workspace
    extension.backend.execute_json.return_value = {"address": "0x123", "workspace": {"id": 1}}

    await extension.run_toggle_special("minimized")

    extension.backend.execute.assert_called_with("movetoworkspacesilent special:minimized,address:0x123")


@pytest.mark.asyncio
async def test_run_toggle_special_restore(extension):
    # Current window is in a special workspace (id < 1)
    # Should toggle special workspace, move back to active, and focus
    extension.backend.execute_json.return_value = {"address": "0x123", "workspace": {"id": -99}}

    await extension.run_toggle_special("minimized")

    expected_calls = [
        "togglespecialworkspace minimized",
        f"movetoworkspacesilent {extension.state.active_workspace},address:0x123",
        "focuswindow address:0x123",
    ]

    extension.backend.execute.assert_called_with(expected_calls)
