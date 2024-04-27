import pytest
from pytest_asyncio import fixture

from .conftest import mocks
from .testtools import wait_called

workspaces = [
    {
        "id": 1,
        "name": "1",
        "monitor": "DP-1",
        "monitorID": 1,
        "windows": 1,
        "hasfullscreen": False,
        "lastwindow": "0x626abe441980",
        "lastwindowtitle": "",
    },
    {
        "id": 9,
        "name": "9",
        "monitor": "DP-1",
        "monitorID": 1,
        "windows": 2,
        "hasfullscreen": False,
        "lastwindow": "0x626abd058570",
        "lastwindowtitle": "top",
    },
    {
        "id": -97,
        "name": "special:special:scratch_term",
        "monitor": "DP-1",
        "monitorID": 1,
        "windows": 1,
        "hasfullscreen": False,
        "lastwindow": "0x626abd12c8e0",
        "lastwindowtitle": "WLR Layout",
    },
    {
        "id": 2,
        "name": "2",
        "monitor": "HDMI-A-1",
        "monitorID": 0,
        "windows": 1,
        "hasfullscreen": True,
        "lastwindow": "0x626abe440390",
        "lastwindowtitle": "",
    },
    {
        "id": 3,
        "name": "3",
        "monitor": "DP-1",
        "monitorID": 1,
        "windows": 4,
        "hasfullscreen": False,
        "lastwindow": "0x626abd0f8170",
        "lastwindowtitle": "~",
    },
    {
        "id": 4,
        "name": "4",
        "monitor": "DP-1",
        "monitorID": 1,
        "windows": 1,
        "hasfullscreen": False,
        "lastwindow": "0x626abe552190",
        "lastwindowtitle": "",
    },
]


@fixture
async def layout_config(monkeypatch):
    "enable the plugin"
    config = {"pyprland": {"plugins": ["workspaces_follow_focus"]}}
    monkeypatch.setattr("tomllib.load", lambda x: config)
    yield


@pytest.mark.asyncio
@pytest.mark.usefixtures("layout_config", "server_fixture")
async def test_layout_center():
    mocks.json_commands_result["workspaces"] = workspaces
    await mocks.send_event("focusedmon>>HDMI-A-1,1")

    await wait_called(mocks.hyprctl)  # Toggle + resize + move
    assert mocks.hyprctl.call_args[0][0][0].startswith("moveworkspacetomonitor")
    mocks.hyprctl.reset_mock()

    await mocks.pypr("change_workspace +1")
    await wait_called(mocks.hyprctl)
    mocks.hyprctl.reset_mock()

    await mocks.pypr("change_workspace -1")
    await wait_called(mocks.hyprctl)
