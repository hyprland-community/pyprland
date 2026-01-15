import pytest
from pytest_asyncio import fixture
from unittest.mock import AsyncMock

from pyprland.plugins.toggle_dpms import Extension


@pytest.fixture
def extension():
    ext = Extension("toggle_dpms")
    ext.backend = AsyncMock()
    # Mocking monitor list
    ext.backend.execute_json = AsyncMock(return_value=[{"name": "DP-1", "dpmsStatus": True}, {"name": "DP-2", "dpmsStatus": True}])
    ext.backend.execute = AsyncMock()
    return ext


@pytest.mark.asyncio
async def test_run_toggle_dpms_off(extension):
    # Initial state: monitors are on (dpmsStatus: True)
    await extension.run_toggle_dpms()
    extension.backend.execute.assert_called_with("dpms off")


@pytest.mark.asyncio
async def test_run_toggle_dpms_on(extension):
    # First call: monitors are ON, should turn OFF
    await extension.run_toggle_dpms()
    extension.backend.execute.assert_called_with("dpms off")

    extension.backend.execute.reset_mock()

    # Change state to OFF for the second call
    extension.backend.execute_json.return_value = [{"name": "DP-1", "dpmsStatus": False}, {"name": "DP-2", "dpmsStatus": False}]

    # Second toggle should turn it on
    await extension.run_toggle_dpms()
    extension.backend.execute.assert_called_with("dpms on")
