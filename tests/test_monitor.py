import asyncio
import pytest
from .conftest import hyprevt_mock, hyprctl_mock, pyprctrl_mock, misc_objects


@pytest.mark.usefixtures("sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_relayout():
    return

    def foo(*a):
        print(">>> hyprctl", a)

    hyprctl_mock[1].write.side_effect = foo

    # await hyprctl_mock[0].q.put(MONITORS)
    # await pyprctrl_mock.q.put(b"relayout\n")
    # await misc_objects['control'](pyprctrl_mock, None)
    await asyncio.sleep(2)


@pytest.mark.usefixtures("empty_config", "server_fixture")
@pytest.mark.asyncio
async def test_nothing():
    await asyncio.sleep(1)
