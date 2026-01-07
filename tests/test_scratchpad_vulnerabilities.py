import asyncio
import pytest
import contextlib
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


class MockProcess:
    _pid_counter = 3001

    def __init__(self, mocker):
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


@fixture
def subprocess_shell_mock(mocker):
    # Reset counter for each test
    MockProcess._pid_counter = 3001

    # Mocking the asyncio.create_subprocess_shell function with incrementing PIDs
    mocked_subprocess_shell = mocker.patch("asyncio.create_subprocess_shell", name="mocked_shell_command")

    async def create_proc(*args, **kwargs):
        p = MockProcess(mocker)
        return p

    mocked_subprocess_shell.side_effect = create_proc
    return mocked_subprocess_shell


@fixture
def mock_subprocess_shell_local(mocker):
    # Reset counter for each test
    MockProcess._pid_counter = 3001

    # Mocking the asyncio.create_subprocess_shell function with incrementing PIDs
    mocked_subprocess_shell = mocker.patch("asyncio.create_subprocess_shell", name="mocked_shell_command")

    async def create_proc(*args, **kwargs):
        p = MockProcess(mocker)
        return p

    mocked_subprocess_shell.side_effect = create_proc
    return mocked_subprocess_shell


@fixture
def mock_aioops(mocker):
    # Mock aiexists to return True for /proc/PID checks, but allow selective failure
    # We'll use a set to track "dead" PIDs
    dead_pids = set()
    # Map PID to process name (comm)
    pid_comm_map = {}

    async def mock_aiexists(path):
        # path format is usually /proc/<pid>
        if path.startswith("/proc/"):
            try:
                parts = path.split("/")
                pid = int(parts[2])
                if pid in dead_pids:
                    return False
            except (ValueError, IndexError):
                pass
        return True

    # Patch modules where aiexists is imported
    mocker.patch("pyprland.aioops.aiexists", side_effect=mock_aiexists)
    mocker.patch("pyprland.plugins.scratchpads.objects.aiexists", side_effect=mock_aiexists)

    # Expose the dead_pids set to tests
    mock_aiexists.dead_pids = dead_pids
    mock_aiexists.pid_comm_map = pid_comm_map

    # Mock aiopen for reading /proc/PID/status and /proc/PID/comm
    mock_file = mocker.MagicMock()

    # Make the file object an async context manager
    async def enter(*args, **kwargs):
        return mock_file

    async def exit(*args, **kwargs):
        return None

    mock_file.__aenter__ = enter
    mock_file.__aexit__ = exit

    # Store current path to know what to return
    current_path = [""]

    # Patch aiopen to return this context manager
    def mock_aiopen(path, *args, **kwargs):
        current_path[0] = path
        # If reading 'comm', prepare the content based on PID
        if path.endswith("/comm"):
            try:
                parts = path.split("/")
                pid = int(parts[2])
                # Default to "ls" (for term) or "pavucontrol" (for volume) if not specified
                # We need a default that matches normal tests
                content = pid_comm_map.get(pid, "ls")  # default to term command

                # Mock read() for comm
                future = asyncio.Future()
                future.set_result(f"{content}\n")
                mock_file.read.return_value = future
            except (ValueError, IndexError):
                pass

        # If reading 'status'
        elif path.endswith("/status"):
            future = asyncio.Future()
            future.set_result(["State: S (sleeping)\n"])
            mock_file.readlines.return_value = future

        return mock_file

    # Patch modules where aiopen is imported
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
    await _send_window_events(address="12345677890", klass="scratch-term")

    await t2

    # 4. Verify Recovery
    assert term_scratch.pid != 3001
    assert term_scratch.pid == 3002  # Should be the next available PID
    assert term_scratch.visible


@fixture
def secure_scratchpads(monkeypatch, mocker):
    d = {
        "pyprland": {"plugins": ["scratchpads"]},
        "scratchpads": {
            "term": {
                "command": "ls",
                "lazy": True,
                "class": "scratch-term",
                "process_tracking": True,
            },
            "volume": {
                "command": "pavucontrol",
                "lazy": True,
                "class": "scratch-volume",
                "process_tracking": True,
            },
        },
    }
    monkeypatch.setattr("tomllib.load", lambda x: d)


@pytest.mark.asyncio
async def test_pid_reuse_conflict(mocker):
    """
    Test that a new process with the same PID but different command
    is detected as 'dead', causing a respawn.
    """
    # 1. Setup mocks
    # Patch aiexists and aiopen directly in objects module
    mock_aiexists = mocker.patch("pyprland.plugins.scratchpads.objects.aiexists", return_value=True)
    # Note: Objects.py imports aiopen as 'aiopen', not as 'aioops.aiopen'.
    # So patching 'objects.aioops' is wrong (hence the AttributeError).

    pid_comm_map = {3001: "term_scratch"}

    @contextlib.asynccontextmanager
    async def mock_aiopen(path, *args, **kwargs):
        # path like /proc/3001/comm or /proc/3001/status
        pid_str = path.split("/")[2]
        if pid_str.isdigit():
            pid = int(pid_str)
            content = pid_comm_map.get(pid, "unknown")

            mock_f = mocker.Mock()
            mock_f.read = mocker.AsyncMock(return_value=content)
            # readlines must return a list of strings, and be awaitable
            mock_f.readlines = mocker.AsyncMock(return_value=["State: S (sleeping)\n"])

            yield mock_f
        else:
            yield mocker.Mock(read=mocker.AsyncMock(return_value=""))

    mocker.patch("pyprland.plugins.scratchpads.objects.aiopen", side_effect=mock_aiopen)

    # 2. Config
    config_data = {
        "scratchpads": {
            "term": {
                "command": "term_scratch",
                "process_tracking": True,
                "class": "term-class",
            }
        }
    }

    # Use side_effect for get which is what we used before
    # And define get_item separately and assign it to the mock's __getitem__
    # but unittest.mock.Mock by default doesn't allow setting magic methods easily unless passed in constructor or using MagicMock

    mock_config = mocker.MagicMock()
    # MagicMock supports magic methods like __getitem__ by default

    mock_config.items.return_value = config_data["scratchpads"].items()
    mock_config.iter_subsections.return_value = config_data["scratchpads"].items()
    mock_config.__getitem__.side_effect = lambda k: config_data["scratchpads"][k]
    mock_config.get.side_effect = config_data["scratchpads"].get

    # 3. Initialize Extension
    from pyprland.plugins.scratchpads import Extension

    ext = Extension("scratchpads")
    ext.config = mock_config
    ext.log = mocker.Mock()

    # We need to mock self.state as well
    ext.state = mocker.Mock()
    ext.state.variables = {}
    ext.state.hyprland_version = mocker.Mock()
    # Mock version comparison
    ext.state.hyprland_version.__lt__ = lambda self, other: False
    ext.state.hyprland_version.__gt__ = lambda self, other: True
    ext.state.monitors = ["monitor1"]

    # Mock hyprctl_json to avoid socket connection
    # Note: ext.hyprctl_json is an instance method, but ipc.get_monitor_props might be using the module level one or a static method.
    # In __init__.py:
    # self.get_monitor_props = staticmethod(partial(get_monitor_props, logger=self.log))
    # get_monitor_props uses hyprctl_json.

    # Mock hyprctl_json to avoid socket connection
    # Note: ext.hyprctl_json is an instance method, but ipc.get_monitor_props might be using the module level one or a static method.
    # In __init__.py:
    # self.get_monitor_props = staticmethod(partial(get_monitor_props, logger=self.log))
    # get_monitor_props uses hyprctl_json.

    # We should mock get_monitor_props directly on the instance to avoid IPC
    mock_monitor = {
        "id": 0,
        "name": "monitor1",
        "width": 1920,
        "height": 1080,
        "x": 0,
        "y": 0,
        "activeWorkspace": {"name": "1"},
        "specialWorkspace": {"name": ""},
        "transform": 0,
        "scale": 1.0,
    }
    ext.get_monitor_props = mocker.AsyncMock(return_value=mock_monitor)

    # We need to mock create_subprocess_shell so we can return a specific PID
    mock_proc = mocker.Mock()
    mock_proc.pid = 3001
    mock_proc.returncode = None
    mock_proc.kill = mocker.Mock()  # Should not be async for subprocess objects
    # communicate must be awaitable
    mock_proc.communicate = mocker.AsyncMock(return_value=(b"", b""))

    # When we 'respawn', we want a NEW pid (e.g. 3002)
    mock_proc_2 = mocker.Mock()
    mock_proc_2.pid = 3002
    mock_proc_2.returncode = None
    mock_proc_2.kill = mocker.Mock()
    mock_proc_2.communicate = mocker.AsyncMock(return_value=(b"", b""))

    async def side_effect_subprocess(cmd):
        # We are mocking the respawn. The first process (3001) was manually injected.
        # So the first call to this mock is the respawn attempt.
        # It should return the new process (3002).
        return mock_proc_2

    mocker.patch("asyncio.create_subprocess_shell", side_effect=side_effect_subprocess)

    # Force the initial state
    await ext.on_reload()

    # Manually register the "alive" state for PID 3001
    term_scratch = ext.scratches.get("term")
    term_scratch.pid = 3001
    ext.procs["term"] = mock_proc

    # Verify it thinks it's alive
    assert await term_scratch.is_alive() is True, "Should be alive initially"

    # 5. Simulate "Death" + PID Reuse
    # "The process died, and cron took PID 3001"
    pid_comm_map[3001] = "cron"

    # Now is_alive() should return False because the name doesn't match 'term_scratch'
    assert await term_scratch.is_alive() is False, "Should detect name mismatch"

    # 6. Trigger Respawn Logic (ensure_alive)
    # ensure_alive checks is_alive(). If false, it calls _start_scratch -> create_subprocess_shell
    # It will also try to call hyprctl to unset windowrules, so we need to mock that
    ext.hyprctl = mocker.AsyncMock()

    # Mock notify_error to avoid IPC
    mocker.patch("pyprland.plugins.scratchpads.notify_error", new=mocker.AsyncMock())
    ext.notify_error = mocker.AsyncMock()

    # We also need to mock __wait_for_client, because it might timeout or fail if we don't mock it well.
    # __wait_for_client checks is_alive and then fetch_matching_client.

    # When we respawn (mock_proc_2), is_alive() will check /proc/3002.
    # We need to map 3002 to 'term_scratch' so it succeeds.
    pid_comm_map[3002] = "term_scratch"

    # We also need fetch_matching_client to succeed or fail gracefully.
    # For now, let's make it succeed so _start_scratch returns True
    term_scratch.fetch_matching_client = mocker.AsyncMock(return_value={"address": "0x123", "pid": 3002})

    await ext.ensure_alive("term")

    # 7. Assertions
    # It should have called start_scratch_command -> create_subprocess_shell (giving us PID 3002)
    assert term_scratch.pid == 3002, f"Should have respawned with new PID 3002, but got {term_scratch.pid}"
    assert ext.procs["term"] == mock_proc_2
