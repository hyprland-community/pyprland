import asyncio
import pytest
from .conftest import hyprevt_mock, hyprctl_mock, pyprctrl_mock, misc_objects


@pytest.mark.usefixtures("empty_config", "server_fixture")
@pytest.mark.asyncio
async def test_nothing():
    await asyncio.sleep(1)


@pytest.mark.usefixtures("sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_relayout():
    return

    def foo(*a):
        print("hyprctl", a)

    hyprctl_mock[1].write.side_effect = foo

    await hyprctl_mock[0].q.put(MONITORS)
    await pyprctrl_mock.q.put(b"relayout\n")
    # await misc_objects['control'](pyprctrl_mock, None)
    await asyncio.sleep(2)


MONITORS = b"""[{
    "id": 1,
    "name": "DP-1",
    "description": "Microstep MAG342CQPV DB6H513700137 (DP-1)",
    "make": "Microstep",
    "model": "MAG342CQPV",
    "serial": "DB6H513700137",
    "width": 3440,
    "height": 1440,
    "refreshRate": 59.99900,
    "x": 0,
    "y": 1080,
    "activeWorkspace": {
        "id": 1,
        "name": "1"
    },
    "specialWorkspace": {
        "id": 0,
        "name": ""
    },
    "reserved": [0, 50, 0, 0],
    "scale": 1.00,
    "transform": 0,
    "focused": true,
    "dpmsStatus": true,
    "vrr": false,
    "activelyTearing": false
},{
    "id": 0,
    "name": "HDMI-A-1",
    "description": "BNQ BenQ PJ 0x01010101 (HDMI-A-1)",
    "make": "BNQ",
    "model": "BenQ PJ",
    "serial": "0x01010101",
    "width": 1920,
    "height": 1080,
    "refreshRate": 60.00000,
    "x": 0,
    "y": 0,
    "activeWorkspace": {
        "id": 4,
        "name": "4"
    },
    "specialWorkspace": {
        "id": 0,
        "name": ""
    },
    "reserved": [0, 50, 0, 0],
    "scale": 1.00,
    "transform": 0,
    "focused": false,
    "dpmsStatus": true,
    "vrr": false,
    "activelyTearing": false
}]"""
