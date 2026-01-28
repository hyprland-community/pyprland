import pytest

from pyprland.plugins.toggle_special import Extension
from tests.conftest import make_extension


@pytest.fixture
def extension():
    return make_extension(Extension)


@pytest.mark.asyncio
async def test_run_toggle_special_minimize(extension):
    # Current window is in a normal workspace (id >= 1)
    # Should move to special workspace
    extension.backend.execute_json.return_value = {"address": "0x123", "workspace": {"id": 1}}

    await extension.run_toggle_special("minimized")

    extension.backend.move_window_to_workspace.assert_called_with("0x123", "special:minimized")


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
