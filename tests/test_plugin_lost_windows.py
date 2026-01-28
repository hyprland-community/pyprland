import pytest
from pyprland.plugins.lost_windows import Extension, contains
from tests.conftest import make_extension


@pytest.fixture
def extension():
    return make_extension(Extension)


def test_contains():
    monitor = {"x": 0, "y": 0, "width": 1920, "height": 1080}

    # Inside
    assert contains(monitor, {"at": [100, 100]}) is True
    assert contains(monitor, {"at": [1919, 1079]}) is True
    assert contains(monitor, {"at": [0, 0]}) is True

    # Outside
    assert contains(monitor, {"at": [-10, 100]}) is False
    assert contains(monitor, {"at": [100, -10]}) is False
    assert contains(monitor, {"at": [1920, 100]}) is False
    assert contains(monitor, {"at": [100, 1080]}) is False


@pytest.mark.asyncio
async def test_run_attract_lost(extension):
    monitor = {"id": 1, "name": "DP-1", "width": 1920, "height": 1080, "x": 0, "y": 0, "focused": True, "activeWorkspace": {"id": 1}}
    monitors = [monitor]

    # One window inside, one lost
    clients = [
        {"pid": 1, "floating": True, "at": [100, 100], "class": "ok"},
        {"pid": 2, "floating": True, "at": [3000, 3000], "class": "lost"},
        {"pid": 3, "floating": False, "at": [3000, 3000], "class": "tiled_lost_ignored"},
    ]

    extension.backend.get_monitors.return_value = monitors
    extension.backend.get_monitor_props.return_value = monitor
    extension.get_clients.return_value = clients

    await extension.run_attract_lost()

    extension.hyprctl.assert_called_once()
    calls = extension.hyprctl.call_args[0][0]

    # Should only move the lost floating window (pid 2)
    assert len(calls) == 2
    assert "pid:2" in calls[0]
    assert "pid:2" in calls[1]
    assert "movetoworkspacesilent 1" in calls[0]
    assert "movewindowpixel exact" in calls[1]
