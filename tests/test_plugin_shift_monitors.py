import pytest
from unittest.mock import Mock

from pyprland.plugins.shift_monitors import Extension
from tests.conftest import make_extension
from tests.testtools import get_executed_commands


@pytest.fixture
def extension():
    ext = make_extension(Extension)
    ext.monitors = ["M1", "M2", "M3"]
    ext.state.environment = "hyprland"  # Default to hyprland for existing tests
    return ext


@pytest.mark.asyncio
async def test_init(extension):
    extension.monitors = []
    extension.backend.get_monitors.return_value = [{"name": "A"}, {"name": "B"}]

    await extension.init()

    assert extension.monitors == ["A", "B"]


@pytest.mark.asyncio
async def test_shift_positive(extension):
    # +1 shift: W1->M2, W2->M3, W3->M1
    # Logic derived: swap(M3, M2) then swap(M2, M1)

    await extension.run_shift_monitors("1")

    commands = get_executed_commands(extension.backend.execute)
    cmd_strings = [c for c, _ in commands]
    # Verify order matters
    assert cmd_strings == ["swapactiveworkspaces M3 M2", "swapactiveworkspaces M2 M1"]


@pytest.mark.asyncio
async def test_shift_negative(extension):
    # -1 shift: W1->M3, W2->M1, W3->M2
    # Logic derived: swap(M1, M2) then swap(M2, M3)

    await extension.run_shift_monitors("-1")

    commands = get_executed_commands(extension.backend.execute)
    cmd_strings = [c for c, _ in commands]
    assert cmd_strings == ["swapactiveworkspaces M1 M2", "swapactiveworkspaces M2 M3"]


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
