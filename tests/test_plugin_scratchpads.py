"""Scratchpad plugin (smoke) tests."""

import asyncio

import pytest
from pytest_asyncio import fixture

from .conftest import mocks
from .testtools import wait_called


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
    return request.param


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


def gen_call_set(call_list: list) -> set[str]:
    """Generate a set of calls from a list of calls."""
    call_set: set[str] = set()
    for item in call_list:
        if isinstance(item, str):
            call_set.add(item)
        else:
            call_set.update(gen_call_set(item))
    return call_set


async def _send_window_events(address="12345677890", klass="kitty-dropterm", title="my fake terminal"):
    await mocks.send_event(f"openwindow>>address:0x{address},1,{klass},{title}")
    await mocks.send_event("activewindowv2>>44444677890")
    await mocks.send_event(f"activewindowv2>>{address}")


@pytest.mark.asyncio
async def test_std(scratchpads, subprocess_shell_mock, server_fixture):
    mocks.json_commands_result["clients"] = CLIENT_CONFIG
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl, count=3)
    await _send_window_events()
    await asyncio.sleep(0.1)
    await wait_called(mocks.hyprctl, count=3)
    call_set = gen_call_set(mocks.hyprctl.call_args_list)
    for expected in {
        "movetoworkspacesilent special:S-term,address:0x12345677890",
        "moveworkspacetomonitor special:S-term DP-1",
        "alterzorder top,address:0x12345677890",
        "focuswindow address:0x12345677890",
        "logger",
        "movetoworkspacesilent 1,address:0x12345677890",
    }:
        assert expected in call_set

    # check if it matches the hide calls
    call_set = gen_call_set(mocks.hyprctl.call_args_list)
    call_set.remove("movetoworkspacesilent special:S-term,address:0x12345677890")
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl, count=4)
    call_set = gen_call_set(mocks.hyprctl.call_args_list)
    call_set.remove("movetoworkspacesilent special:S-term,address:0x12345677890")
    await mocks.send_event("activewindowv2>>44444677890")
    await asyncio.sleep(0.1)
    call_set = gen_call_set(mocks.hyprctl.call_args_list)
    for expected in {
        "moveworkspacetomonitor special:S-term DP-1",
        "alterzorder top,address:0x12345677890",
        "focuswindow address:0x12345677890",
        "movetoworkspacesilent special:S-term,address:0x12345677890",
        "logger",
        "movetoworkspacesilent 1,address:0x12345677890",
    }:
        assert expected in call_set


@pytest.mark.asyncio
async def test_animated(animated_scratchpads, subprocess_shell_mock, server_fixture):
    mocks.json_commands_result["clients"] = CLIENT_CONFIG
    mocks.hyprctl.reset_mock()
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl, count=2)
    call_set = gen_call_set(mocks.hyprctl.call_args_list)
    call_set.remove("movetoworkspacesilent 1,address:0x12345677890")
    call_set.remove("focuswindow address:0x12345677890")
    await _send_window_events()
    await wait_called(mocks.hyprctl, count=4)
    call_set = gen_call_set(mocks.hyprctl.call_args_list)
    #     assert expected in call_set
    mocks.hyprctl.reset_mock()
    await asyncio.sleep(0.2)
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl, count=2)
    await asyncio.sleep(0.2)
    call_set = gen_call_set(mocks.hyprctl.call_args_list)
    call_set.remove("movetoworkspacesilent special:S-term,address:0x12345677890")
    assert any(x.startswith("movewindowpixel") for x in call_set)
    await _send_window_events("7777745", "plop", "notthat")
    await wait_called(mocks.hyprctl, count=2)

    # Test attach
    mocks.hyprctl.reset_mock()
    await mocks.pypr("attach")
    await wait_called(mocks.hyprctl, count=1)
    mocks.hyprctl.reset_mock()
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl, count=3)
    mocks.hyprctl.reset_mock()
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl, count=2)


@pytest.mark.asyncio
async def test_no_proc(no_proc_scratchpads, subprocess_shell_mock, server_fixture):
    mocks.hyprctl.reset_mock()
    mocks.json_commands_result["clients"] = CLIENT_CONFIG
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl, count=2)

    await _send_window_events()
    await wait_called(mocks.hyprctl, count=4)
    await asyncio.sleep(0.2)
    call_set = gen_call_set(mocks.hyprctl.call_args_list)
    call_set.remove("movetoworkspacesilent special:S-term,address:0x12345677890")

    mocks.hyprctl.reset_mock()
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl, count=3)
    call_set = gen_call_set(mocks.hyprctl.call_args_list)
    call_set.remove("movetoworkspacesilent special:S-term,address:0x12345677890")
    assert any(x.startswith("movewindowpixel") for x in call_set)
    await _send_window_events("745", "plop", "notthat")
    await wait_called(mocks.hyprctl, count=2)
    await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_attach_sanity_checks(scratchpads, subprocess_shell_mock, server_fixture):
    """Ensure attaching windows behaves sanely."""
    mocks.json_commands_result["clients"] = CLIENT_CONFIG

    # 1. Start scratchpad
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl, count=3)
    await _send_window_events()
    await asyncio.sleep(0.1)

    # 2. Try to attach scratchpad to itself (should fail/warn)

    # We need to simulate the "active window" being the scratchpad window.
    # The fixture sets up the event loop and state.
    # Calling run_attach reads from self.state.active_window.
    # self.state.active_window is updated via event_activewindowv2

    # Ensure the scratchpad window address is "0x12345677890" (default from _send_window_events)
    # So we send an event saying that window is active.
    await mocks.send_event("activewindowv2>>12345677890")
    await asyncio.sleep(0.05)

    # Clear mocks before calling attach
    mocks.hyprctl.reset_mock()
    mocks.hyprctl.return_value = True

    await mocks.pypr("attach")
    await wait_called(mocks.hyprctl)  # Should call notify_info or error

    # Verify notification about self-attach
    found_notification = False
    for call in mocks.hyprctl.call_args_list:
        args = call[0]
        if isinstance(args, tuple) and len(args) > 1 and args[1] == "notify":
            if "Scratch can't attach to itself" in args[0]:
                found_notification = True
            if "Scratchpad 'term' not found" in args[0]:
                pass

    assert found_notification, "Should notify when attaching scratchpad to itself"


@pytest.mark.asyncio
async def test_attach_workspace_sanity(scratchpads, subprocess_shell_mock, server_fixture):
    """Ensure attaching doesn't move window to wrong workspace."""
    mocks.json_commands_result["clients"] = CLIENT_CONFIG

    # 1. Start scratchpad and show it
    await mocks.pypr("toggle term")
    await _send_window_events()
    await asyncio.sleep(0.1)

    # 2. Focus another window (candidate to be attached)
    other_window_addr = "99999"
    await mocks.send_event(f"activewindowv2>>{other_window_addr}")
    await asyncio.sleep(0.05)

    mocks.hyprctl.reset_mock()

    # 3. Attach the other window
    await mocks.pypr("attach")
    await asyncio.sleep(0.1)

    # 4. Toggle visibility (hide)

    # When hiding, `_hide_scratch` calls `await scratch.update_client_info(clients=clients)`
    # AND `await self._handle_multiwindow(scratch, clients)`
    # AND loop over `extra_addr`:
    #   await self.hyprctl(f"movetoworkspacesilent {mk_scratch_name(scratch.uid)},address:{addr}")

    # So we just need to verify the hyprctl call is made.

    mocks.hyprctl.reset_mock()
    await mocks.pypr("toggle term")
    await asyncio.sleep(0.1)

    call_set = gen_call_set(mocks.hyprctl.call_args_list)

    # Check if the attached window is moved to silent workspace
    moved_attached = False
    for call in call_set:
        if f"movetoworkspacesilent special:S-term,address:0x{other_window_addr}" in call:
            moved_attached = True

    assert moved_attached, "Attached window should be moved to scratchpad workspace on hide"


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
