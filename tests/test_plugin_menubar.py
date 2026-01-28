import pytest
from unittest.mock import Mock, AsyncMock, patch
from pyprland.plugins.menubar import get_pid_from_layers_hyprland, is_bar_in_layers_niri, is_bar_alive, Extension
from tests.conftest import make_extension


def test_get_pid_from_layers_hyprland():
    layers = {
        "DP-1": {
            "levels": {
                "0": [
                    {"namespace": "wallpaper", "pid": 1111},
                ],
                "1": [
                    {"namespace": "bar-123", "pid": 1234},
                ],
            }
        }
    }
    assert get_pid_from_layers_hyprland(layers) == 1234

    layers_no_bar = {
        "DP-1": {
            "levels": {
                "0": [
                    {"namespace": "wallpaper", "pid": 1111},
                ]
            }
        }
    }
    assert get_pid_from_layers_hyprland(layers_no_bar) is False


def test_is_bar_in_layers_niri():
    # Bar exists
    layers = [
        {"namespace": "waybar", "output": "DP-1", "layer": "Top"},
        {"namespace": "bar-123", "output": "DP-1", "layer": "Top"},
    ]
    assert is_bar_in_layers_niri(layers) is True

    # No bar
    layers_no_bar = [
        {"namespace": "waybar", "output": "DP-1", "layer": "Top"},
        {"namespace": "notifications", "output": "DP-1", "layer": "Overlay"},
    ]
    assert is_bar_in_layers_niri(layers_no_bar) is False

    # Empty
    assert is_bar_in_layers_niri([]) is False


@pytest.mark.asyncio
async def test_is_bar_alive_hyprland():
    backend = Mock()
    backend.execute_json = AsyncMock()

    # Case 1: Process exists in /proc
    with patch("os.path.exists", return_value=True):
        assert await is_bar_alive(1234, backend, "hyprland") == 1234
        backend.execute_json.assert_not_called()

    # Case 2: Process not in /proc, but found in layers
    with patch("os.path.exists", return_value=False):
        backend.execute_json.return_value = {"DP-1": {"levels": {"0": [{"namespace": "bar-1", "pid": 5678}]}}}
        assert await is_bar_alive(1234, backend, "hyprland") == 5678
        backend.execute_json.assert_called_with("layers")

    # Case 3: Process not found anywhere
    with patch("os.path.exists", return_value=False):
        backend.execute_json.return_value = {}
        assert await is_bar_alive(1234, backend, "hyprland") is False


@pytest.mark.asyncio
async def test_is_bar_alive_niri():
    backend = Mock()
    backend.execute_json = AsyncMock()

    # Case 1: Process exists in /proc
    with patch("os.path.exists", return_value=True):
        assert await is_bar_alive(1234, backend, "niri") == 1234
        backend.execute_json.assert_not_called()

    # Case 2: Process not in /proc, but found in layers (returns True, not PID)
    with patch("os.path.exists", return_value=False):
        backend.execute_json.return_value = [{"namespace": "bar-1", "output": "DP-1", "layer": "Top"}]
        result = await is_bar_alive(1234, backend, "niri")
        assert result is True  # Niri can only detect presence, not recover PID
        backend.execute_json.assert_called_with("Layers")

    # Case 3: Process not found anywhere
    with patch("os.path.exists", return_value=False):
        backend.execute_json.return_value = []
        assert await is_bar_alive(1234, backend, "niri") is False


@pytest.fixture
def extension():
    # menubar needs state to be a Mock because it accesses active_monitors
    # which is a computed property on SharedState
    state = Mock()
    state.monitors = ["DP-1", "HDMI-A-1", "eDP-1"]
    state.active_monitors = ["DP-1", "HDMI-A-1", "eDP-1"]
    state.environment = "hyprland"
    return make_extension(
        Extension,
        config={"monitors": ["DP-1", "HDMI-A-1"]},
        state=state,
    )


@pytest.mark.asyncio
async def test_get_best_monitor_hyprland(extension):
    # Setup monitors return for Hyprland
    extension.backend.get_monitors.return_value = [
        {"name": "eDP-1", "currentFormat": "1920x1080"},
        {"name": "HDMI-A-1", "currentFormat": "1920x1080"},
    ]

    # "DP-1" is preferred but not available. "HDMI-A-1" is second preferred and available.
    best = await extension.get_best_monitor()
    assert best == "HDMI-A-1"

    # Now let's make DP-1 available
    extension.backend.get_monitors.return_value = [
        {"name": "eDP-1", "currentFormat": "1920x1080"},
        {"name": "HDMI-A-1", "currentFormat": "1920x1080"},
        {"name": "DP-1", "currentFormat": "2560x1440"},
    ]
    best = await extension.get_best_monitor()
    assert best == "DP-1"

    # No preferred monitor available
    extension.config["monitors"] = ["Other"]
    best = await extension.get_best_monitor()
    assert best == ""


@pytest.mark.asyncio
async def test_get_best_monitor_niri(extension):
    extension.state.environment = "niri"

    # Setup outputs return for Niri (dict format, current_mode indicates enabled)
    extension.backend.execute_json.return_value = {
        "eDP-1": {"current_mode": 0, "modes": []},
        "HDMI-A-1": {"current_mode": 0, "modes": []},
    }

    # "DP-1" is preferred but not available. "HDMI-A-1" is second preferred and available.
    best = await extension.get_best_monitor()
    assert best == "HDMI-A-1"

    # Now let's make DP-1 available
    extension.backend.execute_json.return_value = {
        "eDP-1": {"current_mode": 0, "modes": []},
        "HDMI-A-1": {"current_mode": 0, "modes": []},
        "DP-1": {"current_mode": 0, "modes": []},
    }
    best = await extension.get_best_monitor()
    assert best == "DP-1"

    # Disabled monitor (current_mode is None)
    extension.config["monitors"] = ["DP-2", "DP-1"]
    extension.backend.execute_json.return_value = {
        "DP-1": {"current_mode": 0, "modes": []},
        "DP-2": {"current_mode": None, "modes": []},  # Disabled
    }
    best = await extension.get_best_monitor()
    assert best == "DP-1"  # DP-2 is disabled, so DP-1 is selected


@pytest.mark.asyncio
async def test_set_best_monitor(extension):
    extension.get_best_monitor = AsyncMock(return_value="DP-1")
    await extension.set_best_monitor()
    assert extension.cur_monitor == "DP-1"

    # Fallback to state.monitors if get_best_monitor returns empty
    extension.get_best_monitor.return_value = ""
    await extension.set_best_monitor()
    assert extension.cur_monitor == "DP-1"  # first in state.monitors mock
    extension.backend.notify_info.assert_called()


@pytest.mark.asyncio
async def test_event_monitoradded(extension):
    extension.cur_monitor = "HDMI-A-1"  # Index 1 in config
    extension.stop = AsyncMock()
    extension.on_reload = AsyncMock()

    # Add a less preferred monitor
    await extension.event_monitoradded("eDP-1")  # Not in config
    extension.on_reload.assert_not_called()

    # Add a more preferred monitor (DP-1 is index 0)
    await extension.event_monitoradded("DP-1")
    extension.stop.assert_called()
    extension.on_reload.assert_called()


@pytest.mark.asyncio
async def test_run_bar(extension):
    extension.stop = AsyncMock()
    extension.on_reload = AsyncMock()

    await extension.run_bar("start")
    extension.stop.assert_called()
    extension.on_reload.assert_called()

    extension.stop.reset_mock()
    extension.on_reload.reset_mock()

    await extension.run_bar("stop")
    extension.stop.assert_called()
    extension.on_reload.assert_not_called()
