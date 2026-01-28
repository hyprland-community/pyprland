import pytest
from unittest.mock import AsyncMock
from pyprland.plugins.layout_center import Extension
from tests.conftest import make_extension


@pytest.fixture
def extension():
    return make_extension(
        Extension,
        state_active_window="0x1",
        config={"margin": 50, "offset": "10 20"},
        notify_error=AsyncMock(),
        workspace_info={"1": {"enabled": True, "addr": "0x1"}},
    )


@pytest.mark.asyncio
async def test_sanity_check_fails(extension):
    extension.get_clients.return_value = [{"address": "0x1"}]  # Only 1 client
    extension.unprepare_window = AsyncMock()

    assert await extension._sanity_check() is False
    assert extension.enabled is False
    extension.unprepare_window.assert_awaited()


@pytest.mark.asyncio
async def test_sanity_check_passes(extension):
    extension.get_clients.return_value = [{"address": "0x1"}, {"address": "0x2"}]

    assert await extension._sanity_check() is True
    assert extension.enabled is True


@pytest.mark.asyncio
async def test_calculate_geometry(extension):
    monitor = {"name": "DP-1", "focused": True, "scale": 1.0, "width": 1920, "height": 1080, "x": 0, "y": 0, "transform": 0}
    extension.backend.get_monitor_props.return_value = monitor

    # margin 50, offset 10 20
    # width = 1920 - 100 = 1820
    # height = 1080 - 100 = 980
    # x = 0 + 50 + 10 = 60
    # y = 0 + 50 + 20 = 70

    x, y, w, h = await extension._calculate_centered_geometry(50, (10, 20))
    assert x == 60
    assert y == 70
    assert w == 1820
    assert h == 980


@pytest.mark.asyncio
async def test_change_focus_next(extension):
    clients = [{"address": "0x1", "floating": False}, {"address": "0x2", "floating": False}, {"address": "0x3", "floating": False}]
    extension.get_clients.return_value = clients
    extension.main_window_addr = "0x1"
    extension.unprepare_window = AsyncMock()
    extension.prepare_window = AsyncMock()

    # Next from 0x1 (index 0) -> 0x2 (index 1)
    await extension._run_changefocus(1)

    assert extension.main_window_addr == "0x2"
    extension.backend.focus_window.assert_called_with("0x2")


@pytest.mark.asyncio
async def test_change_focus_prev_wrap(extension):
    clients = [{"address": "0x1", "floating": False}, {"address": "0x2", "floating": False}, {"address": "0x3", "floating": False}]
    extension.get_clients.return_value = clients
    extension.main_window_addr = "0x1"
    extension.unprepare_window = AsyncMock()
    extension.prepare_window = AsyncMock()

    # Prev from 0x1 (index 0) -> 0x3 (index 2) - Wrap around
    await extension._run_changefocus(-1)

    assert extension.main_window_addr == "0x3"
    extension.backend.focus_window.assert_called_with("0x3")
