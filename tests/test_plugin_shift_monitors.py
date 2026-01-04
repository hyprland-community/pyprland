import pytest
from unittest.mock import Mock, AsyncMock, call
from pyprland.plugins.shift_monitors import Extension


@pytest.fixture
def extension():
    ext = Extension("shift_monitors")
    ext.hyprctl = AsyncMock()
    ext.hyprctl_json = AsyncMock()
    ext.monitors = ["M1", "M2", "M3"]
    return ext


@pytest.mark.asyncio
async def test_init(extension):
    extension.monitors = []
    extension.hyprctl_json.return_value = [{"name": "A"}, {"name": "B"}]

    await extension.init()

    assert extension.monitors == ["A", "B"]


@pytest.mark.asyncio
async def test_shift_positive(extension):
    # +1 shift: W1->M2, W2->M3, W3->M1
    # Logic derived: swap(M3, M2) then swap(M2, M1)

    await extension.run_shift_monitors("1")

    assert extension.hyprctl.call_count == 2
    # Verify order matters
    extension.hyprctl.assert_has_calls([call("swapactiveworkspaces M3 M2"), call("swapactiveworkspaces M2 M1")])


@pytest.mark.asyncio
async def test_shift_negative(extension):
    # -1 shift: W1->M3, W2->M1, W3->M2
    # Logic derived: swap(M1, M2) then swap(M2, M3)

    await extension.run_shift_monitors("-1")

    assert extension.hyprctl.call_count == 2
    extension.hyprctl.assert_has_calls([call("swapactiveworkspaces M1 M2"), call("swapactiveworkspaces M2 M3")])


@pytest.mark.asyncio
async def test_monitor_events(extension):
    await extension.event_monitoradded("M4")
    assert extension.monitors == ["M1", "M2", "M3", "M4"]

    await extension.event_monitorremoved("M1")
    assert extension.monitors == ["M2", "M3", "M4"]

    # Removing non-existent shouldn't crash
    extension.log = Mock()
    await extension.event_monitorremoved("ghost")
    extension.log.warning.assert_called()
