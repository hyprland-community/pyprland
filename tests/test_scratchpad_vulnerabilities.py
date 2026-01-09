import asyncio
import pytest
from pytest_asyncio import fixture
from .conftest import mocks
from .testtools import wait_called
from unittest.mock import AsyncMock


# Setup two scratchpads for multi-scratchpad tests
@fixture
def multi_scratchpads(monkeypatch, mocker):
    d = {
        "pyprland": {"plugins": ["scratchpads"]},
        "scratchpads": {
            "term": {
                "command": "ls",
                "lazy": True,
                "class": "scratch-term",
                "process_tracking": False,
            },
            "volume": {
                "command": "pavucontrol",
                "lazy": True,
                "class": "scratch-volume",
                "process_tracking": False,
            },
        },
    }
    monkeypatch.setattr("tomllib.load", lambda x: d)


@fixture
def subprocess_shell_mock(mocker):
    # Mocking the asyncio.create_subprocess_shell function with incrementing PIDs
    mocked_subprocess_shell = mocker.patch("asyncio.create_subprocess_shell", name="mocked_shell_command")

    class MockProcess:
        _pid_counter = 3001

        def __init__(self):
            self.pid = MockProcess._pid_counter
            MockProcess._pid_counter += 1
            self.stderr = AsyncMock(return_code="")
            self.stdout = AsyncMock(return_code="")
            self.terminate = mocker.Mock()
            self.wait = AsyncMock()
            self.kill = mocker.Mock()
            self.returncode = 0

        async def communicate(self):
            return b"", b""

    async def create_proc(*args, **kwargs):
        return MockProcess()

    mocked_subprocess_shell.side_effect = create_proc
    return mocked_subprocess_shell


@fixture
def mock_aioops(mocker):
    # Mock aiexists to return True for /proc/PID checks, but allow selective failure
    # We'll use a set to track "dead" PIDs
    dead_pids = set()

    async def mock_aiexists(path):
        # path format is usually /proc/<pid>
        if path.startswith("/proc/"):
            try:
                pid = int(path.split("/")[2])
                if pid in dead_pids:
                    return False
            except (ValueError, IndexError):
                pass
        return True

    # Patch aiexists in both locations
    mocker.patch("pyprland.aioops.aiexists", side_effect=mock_aiexists)
    mocker.patch("pyprland.plugins.scratchpads.objects.aiexists", side_effect=mock_aiexists)

    # Expose the dead_pids set to tests
    mock_aiexists.dead_pids = dead_pids

    # Mock aiopen for reading /proc/PID/status
    mock_file = mocker.MagicMock()

    # Make readlines return a list (it's awaited in the code: await f.readlines())
    future = asyncio.Future()
    future.set_result(["State: S (sleeping)\n"])
    mock_file.readlines.return_value = future

    # Make the file object an async context manager
    async def enter(*args, **kwargs):
        return mock_file

    async def exit(*args, **kwargs):
        return None

    mock_file.__aenter__ = enter
    mock_file.__aexit__ = exit

    # Patch aiopen to return this context manager
    def mock_aiopen(*args, **kwargs):
        return mock_file

    mocker.patch("pyprland.aioops.aiopen", side_effect=mock_aiopen)
    mocker.patch("pyprland.plugins.scratchpads.objects.aiopen", side_effect=mock_aiopen)
    return mock_aiexists


def gen_call_set(call_list: list) -> set[str]:
    """Generate a set of calls from a list of calls."""
    call_set: set[str] = set()
    for item in call_list:
        if isinstance(item, str):
            call_set.add(item)
        else:
            call_set.update(gen_call_set(item))
    return call_set


async def _send_window_events(address="12345677890", klass="scratch-term", title="my fake terminal"):
    await mocks.send_event(f"openwindow>>address:0x{address},1,{klass},{title}")
    await mocks.send_event("activewindowv2>>44444677890")
    await mocks.send_event(f"activewindowv2>>{address}")


CLIENT_CONFIG = [
    {
        "address": "0x12345677890",  # term
        "mapped": True,
        "hidden": False,
        "at": [100, 100],
        "size": [500, 500],
        "workspace": {"id": 1, "name": "1"},
        "floating": False,
        "monitor": 0,
        "class": "scratch-term",
        "title": "my fake terminal",
        "pid": 1001,  # Matches MockProcess first PID
        "pinned": False,
    },
    {
        "address": "0xabcdef12345",  # volume
        "mapped": True,
        "hidden": False,
        "at": [200, 200],
        "size": [400, 400],
        "workspace": {"id": 1, "name": "1"},
        "floating": False,
        "monitor": 0,
        "class": "scratch-volume",
        "title": "volume control",
        "pid": 1002,  # Matches MockProcess second PID
        "pinned": False,
    },
    {
        "address": "0x99999999999",  # independent client
        "mapped": True,
        "hidden": False,
        "at": [300, 300],
        "size": [600, 600],
        "workspace": {"id": 1, "name": "1"},
        "floating": False,
        "monitor": 0,
        "class": "firefox",
        "title": "browser",
        "pid": 2001,
        "pinned": False,
    },
]


@pytest.mark.asyncio
async def test_shared_custody_conflict(multi_scratchpads, subprocess_shell_mock, server_fixture, mock_aioops):
    """
    Test 1: The 'Shared Custody' Conflict
    Verify behavior when a single window is attached to two different scratchpads simultaneously.
    """
    mocks.json_commands_result["clients"] = CLIENT_CONFIG

    # 1. Initialize scratchpads
    # We must ensure they are "alive" so they can be shown/hidden

    # Start the toggle task for term
    t1 = asyncio.create_task(mocks.pypr("toggle term"))
    await asyncio.sleep(0.5)
    # Simulate window appearance
    await _send_window_events(address="12345677890", klass="scratch-term")
    await t1  # Wait for toggle to complete successfully

    # Start the toggle task for volume
    t2 = asyncio.create_task(mocks.pypr("toggle volume"))
    await asyncio.sleep(0.5)
    await _send_window_events(address="abcdef12345", klass="scratch-volume")
    await t2

    mocks.hyprctl.reset_mock()

    # 2. Focus independent client
    client_addr = "99999999999"
    await mocks.send_event(f"activewindowv2>>{client_addr}")
    await asyncio.sleep(0.05)

    # 3. Attach client to 'term'

    # Focus term window (this sets self.last_focused to 'term')
    await mocks.send_event("activewindowv2>>12345677890")
    await asyncio.sleep(0.05)

    # Focus client (this is the window to be attached)
    await mocks.send_event(f"activewindowv2>>{client_addr}")
    await asyncio.sleep(0.05)

    # Attach to term
    mocks.hyprctl.reset_mock()
    await mocks.pypr("attach")
    # Note: attach might not call hyprctl if "pinned" is False or if it fails silently,
    # but with default config "pinned" is True, so it should call "pin address:..."
    await wait_called(mocks.hyprctl)

    # 4. Attach client to 'volume'
    # Focus volume window (sets self.last_focused to 'volume')
    await mocks.send_event("activewindowv2>>abcdef12345")
    await asyncio.sleep(0.05)

    # Focus client
    await mocks.send_event(f"activewindowv2>>{client_addr}")
    await asyncio.sleep(0.05)

    # Attach to volume
    mocks.hyprctl.reset_mock()
    await mocks.pypr("attach")
    await wait_called(mocks.hyprctl)

    # 5. Hide 'term'
    # Should hide 'term' BUT NOT the client (because volume stole it)
    mocks.hyprctl.reset_mock()
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl)

    call_set = gen_call_set(mocks.hyprctl.call_args_list)

    # Verify client is NOT moved to special workspace (hidden)
    moved_client = any(f"movetoworkspacesilent special:S-term,address:0x{client_addr}" in str(c) for c in call_set)
    assert not moved_client, "Client should NOT be hidden when 'term' is toggled off (volume has custody)"

    # 6. Hide 'volume'
    # 'volume' thinks it also owns the client. It should hide it.
    mocks.hyprctl.reset_mock()
    await mocks.pypr("toggle volume")
    await wait_called(mocks.hyprctl)

    call_set = gen_call_set(mocks.hyprctl.call_args_list)
    print(f"Call set for volume hide: {call_set}")

    # The client should be moved to special:S-volume
    moved_client_vol = any(f"movetoworkspacesilent special:S-volume,address:0x{client_addr}" in str(c) for c in call_set)
    assert moved_client_vol, "Client should be moved to volume scratchpad when volume is hidden"

    # 7. Show 'term'
    # It will try to bring back the client from special:S-term, but it is in special:S-volume (or wherever volume put it)
    mocks.hyprctl.reset_mock()
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl)

    call_set = gen_call_set(mocks.hyprctl.call_args_list)

    # Check if it brings the client back
    brought_back = False
    for call in call_set:
        if f"address:0x{client_addr}" in call and "movetoworkspacesilent 1" in call:
            brought_back = True

    assert not brought_back, "Client should NOT be brought back when 'term' is shown, because 'volume' stole it"


@pytest.mark.asyncio
async def test_zombie_process_recovery(multi_scratchpads, subprocess_shell_mock, server_fixture, mock_aioops):
    """
    Test 2: The 'Zombie' State (Process Desync)
    Verify that if a scratchpad process dies (e.g. kill -9), the plugin detects it and respawns.
    """
    # Start with NO clients
    mocks.json_commands_result["clients"] = []

    # 1. Start 'term' normally
    mocks.hyprctl.reset_mock()
    t1 = asyncio.create_task(mocks.pypr("toggle term"))
    await asyncio.sleep(0.5)

    # Now update clients to show it started with PID 3001
    CLIENT_CONFIG[0]["pid"] = 3001
    mocks.json_commands_result["clients"] = [CLIENT_CONFIG[0]]

    await _send_window_events(address="12345677890", klass="scratch-term")
    await t1

    # Verify it started
    from pyprland.command import Pyprland

    manager = Pyprland.instance
    plugin = manager.plugins["scratchpads"]
    term_scratch = plugin.scratches.get("term")
    assert term_scratch.pid == 3001
    assert await term_scratch.is_alive()

    # 2. Simulate "kill -9" (Process disappears from /proc)
    mock_aioops.dead_pids.add(3001)

    # To test zombie recovery, we MUST enable process_tracking.
    term_scratch.conf.ref["process_tracking"] = True

    assert not await term_scratch.is_alive()

    # 3. Toggle 'term' again
    # Expected: Plugin detects death -> Respawns (PID 3002) -> Shows window
    mocks.hyprctl.reset_mock()

    t2 = asyncio.create_task(mocks.pypr("toggle term"))
    await asyncio.sleep(0.5)  # Wait for it to try spawning

    # Update clients to show the NEW process (PID 3002)
    # We simulate that the old window is gone/dead, and a new one appeared with new PID
    CLIENT_CONFIG[0]["pid"] = 3002
    mocks.json_commands_result["clients"] = [CLIENT_CONFIG[0]]

    # Send events for the NEW window
    # Update the address to match what _send_window_events uses, or update the client config to match
    # CLIENT_CONFIG[0] already has address="0x12345677890" which matches "12345677890" used in _send_window_events
    # The issue might be timing or how `wait_for_client` checks visibility.
    # But wait, we are reusing the SAME address "12345677890" for the new window.
    # The plugin might still have the old window info with that address.

    # In a real scenario, a new window might have a different address.
    # Let's try changing the address for the "respawned" window to be safe.
    new_addr = "12345677999"
    CLIENT_CONFIG[0]["address"] = f"0x{new_addr}"
    mocks.json_commands_result["clients"] = [CLIENT_CONFIG[0]]

    await _send_window_events(address=new_addr, klass="scratch-term")

    await t2

    # 4. Verify Recovery
    assert term_scratch.pid != 3001
    assert term_scratch.pid == 3002  # Should be the next available PID
    assert term_scratch.visible

    # Check that we actually ran the spawn command again
    # subprocess_shell_mock should have been called twice (once init, once respawn)
    assert subprocess_shell_mock.call_count == 2
