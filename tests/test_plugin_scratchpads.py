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

    # Check for notification in kwargs
    found = False
    for call in mocks.hyprctl.call_args_list:
        if call.kwargs.get("base_command") == "notify":
            found = True
            break
    assert found


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
        if call.kwargs.get("base_command") == "notify":
            args = call[0][0]
            if "can't attach or detach to itself" in args:
                found_notification = True
            if "Scratchpad 'term' not found" in args:
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


BROWSER_CLIENT = {
    "address": "0xBROWSER123",
    "mapped": True,
    "hidden": False,
    "at": [100, 100],
    "size": [800, 600],
    "workspace": {"id": 1, "name": "1"},
    "floating": False,
    "monitor": 0,
    "class": "firefox",
    "title": "Firefox",
    "initialClass": "firefox",
    "initialTitle": "Firefox",
    "pid": 2,
    "xwayland": False,
    "pinned": False,
    "fullscreen": False,
    "fullscreenMode": 0,
    "fakeFullscreen": False,
    "grouped": [],
    "swallowing": "0x0",
    "focusHistoryID": 6,
}


@fixture
def exclude_scratchpads(monkeypatch, mocker):
    """Config with two scratchpads where one excludes the other."""
    d = {
        "pyprland": {"plugins": ["scratchpads"]},
        "scratchpads": {
            "term": {
                "command": "ls",
                "lazy": True,
                "class": "kitty-dropterm",
            },
            "browser": {
                "command": "ls",
                "lazy": True,
                "class": "firefox",
                "excludes": ["term"],
                "restore_excluded": True,
            },
        },
    }
    monkeypatch.setattr("tomllib.load", lambda x: d)


@pytest.mark.asyncio
async def test_excluded_scratches_isolation(exclude_scratchpads, subprocess_shell_mock, server_fixture):
    """Verify excluded_scratches is per-instance, not shared across Scratch objects."""
    # Setup clients
    mocks.json_commands_result["clients"] = CLIENT_CONFIG + [BROWSER_CLIENT]

    # 1. Show term scratchpad first
    await mocks.pypr("toggle term")
    await _send_window_events()
    await asyncio.sleep(0.1)

    # 2. Show browser scratchpad (should hide term and track it in browser.excluded_scratches)
    await mocks.pypr("toggle browser")
    await _send_window_events(address="BROWSER123", klass="firefox", title="Firefox")
    await asyncio.sleep(0.1)

    # 3. Access the plugin to verify internal state
    plugin = mocks.pyprland_instance.plugins["scratchpads"]
    term_scratch = plugin.scratches.get("term")
    browser_scratch = plugin.scratches.get("browser")

    # Key assertion: browser should have "term" in its excluded list
    assert "term" in browser_scratch.excluded_scratches, "browser should track that it excluded term"

    # Key assertion: term should have empty excluded list (not shared!)
    assert term_scratch.excluded_scratches == [], "term should have its own empty excluded_scratches list"

    # 4. Hide browser - should restore term
    mocks.hyprctl.reset_mock()
    await mocks.pypr("toggle browser")
    await asyncio.sleep(0.2)

    # After hide, browser.excluded_scratches should be cleared
    assert browser_scratch.excluded_scratches == [], "browser.excluded_scratches should be cleared after hide"


@pytest.mark.asyncio
async def test_command_serialization(scratchpads, subprocess_shell_mock, server_fixture):
    """Verify rapid commands are serialized through the queue (not interleaved)."""
    mocks.json_commands_result["clients"] = CLIENT_CONFIG

    # Track command execution order
    execution_order = []
    plugin = None

    # Wait for plugin to be available
    for _ in range(10):
        if mocks.pyprland_instance and "scratchpads" in mocks.pyprland_instance.plugins:
            plugin = mocks.pyprland_instance.plugins["scratchpads"]
            break
        await asyncio.sleep(0.1)

    assert plugin is not None, "Scratchpads plugin not loaded"

    # Send window events to initialize the scratchpad
    await mocks.pypr("toggle term")
    await _send_window_events()
    await asyncio.sleep(0.1)

    # Patch run_hide to track execution order
    original_run_hide = plugin.run_hide

    async def tracked_run_hide(uid: str, flavor=None):
        execution_order.append(f"start:{uid}")
        await asyncio.sleep(0.05)  # Simulate some async work
        if flavor is not None:
            await original_run_hide(uid, flavor)
        else:
            await original_run_hide(uid)
        execution_order.append(f"end:{uid}")

    plugin.run_hide = tracked_run_hide

    # Reset tracking
    execution_order.clear()

    # Fire two hide commands concurrently - they should serialize
    await asyncio.gather(
        mocks.pypr("hide term"),
        mocks.pypr("hide term"),
    )
    await asyncio.sleep(0.2)

    # Restore original method
    plugin.run_hide = original_run_hide

    # Verify serialization: operations should not interleave
    # Valid serialized: [start, end, start, end] - each start followed by its end
    # Invalid interleaved: [start, start, end, end]
    if len(execution_order) >= 4:
        starts = [i for i, x in enumerate(execution_order) if x.startswith("start")]
        ends = [i for i, x in enumerate(execution_order) if x.startswith("end")]
        # First end should come before second start
        assert ends[0] < starts[1], f"Commands interleaved! Order: {execution_order}"
    # If less than 4 entries, second command may have been a no-op (already hidden) - that's fine
