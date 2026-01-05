import pytest
from unittest.mock import Mock, AsyncMock, patch
from pyprland.plugins.menubar import get_pid_from_layers, is_bar_alive, Extension


def test_get_pid_from_layers():
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
    assert get_pid_from_layers(layers) == 1234

    layers_no_bar = {
        "DP-1": {
            "levels": {
                "0": [
                    {"namespace": "wallpaper", "pid": 1111},
                ]
            }
        }
    }
    assert get_pid_from_layers(layers_no_bar) is False


@pytest.mark.asyncio
async def test_is_bar_alive():
    hyprctl_json = AsyncMock()

    # Case 1: Process exists in /proc
    with patch("os.path.exists", return_value=True):
        assert await is_bar_alive(1234, hyprctl_json) == 1234
        hyprctl_json.assert_not_called()

    # Case 2: Process not in /proc, but found in layers
    with patch("os.path.exists", return_value=False):
        hyprctl_json.return_value = {"DP-1": {"levels": {"0": [{"namespace": "bar-1", "pid": 5678}]}}}
        assert await is_bar_alive(1234, hyprctl_json) == 5678
        hyprctl_json.assert_called_with("layers")

    # Case 3: Process not found anywhere
    with patch("os.path.exists", return_value=False):
        hyprctl_json.return_value = {}
        assert await is_bar_alive(1234, hyprctl_json) is False


@pytest.fixture
def extension():
    ext = Extension("menubar")
    ext.hyprctl_json = AsyncMock()
    ext.notify_info = AsyncMock()
    ext.log = Mock()
    ext.config = {"monitors": ["DP-1", "HDMI-A-1"]}
    ext.state = Mock()
    ext.state.monitors = ["DP-1", "HDMI-A-1", "eDP-1"]
    return ext


@pytest.mark.asyncio
async def test_get_best_monitor(extension):
    # Setup monitors return
    extension.hyprctl_json.return_value = [
        {"name": "eDP-1", "currentFormat": "1920x1080"},
        {"name": "HDMI-A-1", "currentFormat": "1920x1080"},
    ]

    # "DP-1" is preferred but not available. "HDMI-A-1" is second preferred and available.
    best = await extension.get_best_monitor()
    assert best == "HDMI-A-1"

    # Now let's make DP-1 available
    extension.hyprctl_json.return_value = [
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
async def test_set_best_monitor(extension):
    extension.get_best_monitor = AsyncMock(return_value="DP-1")
    await extension.set_best_monitor()
    assert extension.cur_monitor == "DP-1"

    # Fallback to state.monitors if get_best_monitor returns empty
    extension.get_best_monitor.return_value = ""
    await extension.set_best_monitor()
    assert extension.cur_monitor == "DP-1"  # first in state.monitors mock
    extension.notify_info.assert_called()


@pytest.mark.asyncio
async def test_event_monitoradded(extension):
    extension.cur_monitor = "HDMI-A-1"  # Index 1 in config
    extension.kill = Mock()
    extension.on_reload = AsyncMock()

    # Add a less preferred monitor
    await extension.event_monitoradded("eDP-1")  # Not in config
    extension.on_reload.assert_not_called()

    # Add a more preferred monitor (DP-1 is index 0)
    await extension.event_monitoradded("DP-1")
    extension.kill.assert_called()
    extension.on_reload.assert_called()


@pytest.mark.asyncio
async def test_run_bar(extension):
    extension.kill = Mock()
    extension.on_reload = AsyncMock()

    await extension.run_bar("start")
    extension.kill.assert_called()
    extension.on_reload.assert_called()

    extension.kill.reset_mock()
    extension.on_reload.reset_mock()

    await extension.run_bar("stop")
    extension.kill.assert_called()
    extension.on_reload.assert_not_called()
