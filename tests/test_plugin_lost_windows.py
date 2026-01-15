import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from pyprland.plugins.lost_windows import Extension, contains


@pytest.fixture
def extension():
    ext = Extension("lost_windows")
    ext.backend = AsyncMock()
    ext.hyprctl = ext.backend.execute
    ext.hyprctl_json = ext.backend.execute_json
    ext.get_clients = AsyncMock()
    return ext


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
    monitors = [{"id": 1, "name": "DP-1", "width": 1920, "height": 1080, "x": 0, "y": 0, "focused": True, "activeWorkspace": {"id": 1}}]

    # One window inside, one lost
    clients = [
        {"pid": 1, "floating": True, "at": [100, 100], "class": "ok"},
        {"pid": 2, "floating": True, "at": [3000, 3000], "class": "lost"},
        {"pid": 3, "floating": False, "at": [3000, 3000], "class": "tiled_lost_ignored"},
    ]

    extension.hyprctl_json.return_value = monitors
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
