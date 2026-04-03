import pytest
from unittest.mock import AsyncMock

from pyprland.plugins.toggle_dpms import Extension
from tests.conftest import make_extension
from tests.testtools import get_executed_commands


@pytest.fixture
def extension():
    ext = make_extension(Extension)
    # Mocking monitor list
    ext.backend.get_monitors = AsyncMock(return_value=[{"name": "DP-1", "dpmsStatus": True}, {"name": "DP-2", "dpmsStatus": True}])
    return ext


@pytest.mark.asyncio
async def test_run_toggle_dpms_off(extension):
    # Initial state: monitors are on (dpmsStatus: True)
    await extension.run_toggle_dpms()
    commands = get_executed_commands(extension.backend.execute)
    assert ("dpms off", {}) in commands


@pytest.mark.asyncio
async def test_run_toggle_dpms_on(extension):
    # First call: monitors are ON, should turn OFF
    await extension.run_toggle_dpms()
    commands = get_executed_commands(extension.backend.execute)
    assert ("dpms off", {}) in commands

    extension.backend.execute.reset_mock()

    # Change state to OFF for the second call
    extension.backend.get_monitors.return_value = [{"name": "DP-1", "dpmsStatus": False}, {"name": "DP-2", "dpmsStatus": False}]

    # Second toggle should turn it on
    await extension.run_toggle_dpms()
    commands = get_executed_commands(extension.backend.execute)
    assert ("dpms on", {}) in commands
