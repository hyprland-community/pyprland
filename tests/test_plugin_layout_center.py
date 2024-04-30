import pytest
from pytest_asyncio import fixture

from .conftest import mocks
from .testtools import wait_called


@fixture
async def layout_config(monkeypatch):
    "enable the plugin"
    config = {"pyprland": {"plugins": ["layout_center"]}}
    monkeypatch.setattr("tomllib.load", lambda x: config)
    yield


def make_client(**kw):
    d = {
        "address": "0x333333333333",
        "mapped": True,
        "hidden": False,
        "at": [760, 0],
        "size": [1920, 1080],
        "workspace": {"id": 1, "name": "1"},
        "floating": False,
        "monitor": 0,
        "class": "brave-browser",
        "title": "YYYY",
        "initialClass": "brave-browser",
        "initialTitle": "XXXX",
        "pid": 26787,
        "xwayland": False,
        "pinned": False,
        "fullscreen": True,
        "fullscreenMode": 0,
        "fakeFullscreen": False,
        "grouped": [],
        "swallowing": "0x0",
        "focusHistoryID": 1,
    }
    d.update(kw)
    return d


@pytest.mark.asyncio
@pytest.mark.usefixtures("layout_config", "server_fixture")
async def test_layout_center():
    await mocks.send_event("activewindowv2>>123456789")
    import asyncio

    await asyncio.sleep(0.1)
    mocks.json_commands_result["clients"] = [
        make_client(address="0x123456789"),
        make_client(address="0x987654321"),
    ]

    print("toggle:")
    await mocks.pypr("layout_center toggle")
    await wait_called(mocks.hyprctl, count=3)  # Toggle + resize + move
    cmd = mocks.hyprctl.call_args[0][0]
    assert cmd.startswith("movewindowpixel") and "123456789" in cmd
    print(mocks.hyprctl.call_args_list)
    mocks.hyprctl.reset_mock()
    mocks.json_commands_result["clients"][0]["floating"] = True

    print("next:")
    await mocks.pypr("layout_center next")
    await wait_called(mocks.hyprctl, count=4)
    print(mocks.hyprctl.call_args_list)
    await mocks.send_event("activewindowv2>>987654321")
    mocks.hyprctl.reset_mock()
    mocks.json_commands_result["clients"][0]["floating"] = False
    mocks.json_commands_result["clients"][1]["floating"] = True

    print("toggle:")
    await mocks.pypr("layout_center toggle")
    await wait_called(mocks.hyprctl, count=1)
    await asyncio.sleep(0.1)
    print(mocks.hyprctl.call_args_list)
    assert mocks.hyprctl.call_args[0][0].startswith("togglefloating")
