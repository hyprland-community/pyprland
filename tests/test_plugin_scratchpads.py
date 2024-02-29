import asyncio
from pytest_asyncio import fixture
from .conftest import mocks
from .testtools import wait_called
import pytest


@fixture
def scratchpads(monkeypatch, mocker):
    d = {
        "pyprland": {"plugins": ["scratchpads"]},
        "scratchpads": {
            "term": {
                "command": "ls",
                "lazy": True,
            }
        },
    }
    monkeypatch.setattr("tomllib.load", lambda x: d)


@fixture(params=["fromTop", "fromBottom", "fromLeft", "fromRight"])
def animated_scratchpads(request, monkeypatch, mocker):
    d = {
        "pyprland": {"plugins": ["scratchpads"]},
        "scratchpads": {
            "term": {
                "command": "ls",
                "lazy": True,
                "class": "kitty-dropterm",
                "animation": request.param,
            }
        },
    }
    monkeypatch.setattr("tomllib.load", lambda x: d)


@fixture
def no_proc_scratchpads(request, monkeypatch, mocker):
    d = {
        "pyprland": {"plugins": ["scratchpads"]},
        "scratchpads": {
            "term": {
                "command": "ls",
                "lazy": True,
                "class": "kitty-dropterm",
                "process_tracking": False,
                "animation": "fromLeft",
            }
        },
    }
    monkeypatch.setattr("tomllib.load", lambda x: d)


@pytest.mark.asyncio
async def test_not_found(scratchpads, subprocess_shell_mock, server_fixture):
    await mocks.pypr("toggle foobar")
    await wait_called(mocks.hyprctl)

    assert mocks.hyprctl.call_args[0][1] == "notify"


@pytest.mark.asyncio
async def test_std(scratchpads, subprocess_shell_mock, server_fixture):
    mocks.json_commands_result["clients"] = CLIENT_CONFIG
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl, count=3)
    await asyncio.sleep(0.2)
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl, count=4)


@pytest.mark.asyncio
async def test_animated(animated_scratchpads, subprocess_shell_mock, server_fixture):
    mocks.json_commands_result["clients"] = CLIENT_CONFIG
    mocks.hyprctl.reset_mock()
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl, count=3)
    assert mocks.hyprctl.call_args_list[-1][0][0].startswith("focuswindow")
    mocks.hyprctl.reset_mock()
    await asyncio.sleep(0.3)
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl, count=2)
    assert mocks.hyprctl.call_args[0][0].startswith("focuswindow")
    await mocks.pypr("reload")
    await asyncio.sleep(0.3)


@pytest.mark.asyncio
async def test_no_proc(no_proc_scratchpads, subprocess_shell_mock, server_fixture):
    mocks.json_commands_result["clients"] = CLIENT_CONFIG
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl, count=4)
    await asyncio.sleep(0.2)
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl, count=6)


CLIENT_CONFIG = [
    {
        "address": "0x12345677890",
        "mapped": True,
        "hidden": False,
        "at": [2355, 54],
        "size": [768, 972],
        "workspace": {"id": 1, "name": "1"},
        "floating": False,
        "monitor": 0,
        "class": "kitty-dropterm",
        "title": "my fake terminal",
        "initialClass": "kitty",
        "initialTitle": "blah",
        "pid": 1,
        "xwayland": False,
        "pinned": False,
        "fullscreen": False,
        "fullscreenMode": 0,
        "fakeFullscreen": False,
        "grouped": [],
        "swallowing": "0x0",
        "focusHistoryID": 5,
    },
]
