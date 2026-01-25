"""generic fixtures."""

from __future__ import annotations

import asyncio
import logging
import os
from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
import tomllib
from pytest_asyncio import fixture

from .testtools import MockReader, MockWriter

if TYPE_CHECKING:
    from pyprland.manager import Pyprland

os.environ["HYPRLAND_INSTANCE_SIGNATURE"] = "ABCD"

CONFIG_1 = tomllib.load(open("tests/sample_config.toml", "rb"))


@pytest.fixture
def test_logger():
    """Provide a silent logger for tests."""
    logger = logging.getLogger("test")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


# Error patterns to detect in stderr during tests
ERROR_PATTERNS = [
    "failed:",
    "Error:",
    "ERROR",
    "Exception",
    "Traceback",
]

# Patterns to ignore (false positives)
ERROR_IGNORE_PATTERNS = [
    "notify_error",  # Method name, not an actual error
    "ConnectionResetError",  # Expected in some cleanup scenarios
    "BrokenPipeError",  # Expected in some cleanup scenarios
    "DeprecationWarning",  # Python deprecation warnings
    "Config error for",  # Validation errors from run_validate command (expected in tests)
]


def pytest_configure():
    """Runs once before all."""
    os.environ["PYPRLAND_STRICT_ERRORS"] = "1"
    from pyprland.common import init_logger

    init_logger("/dev/null", force_debug=True)


def _contains_error(text: str) -> str | None:
    """Check if text contains error patterns, returns the matching line or None."""
    for line in text.split("\n"):
        # Skip ignored patterns
        if any(ignore in line for ignore in ERROR_IGNORE_PATTERNS):
            continue
        # Check for error patterns
        for pattern in ERROR_PATTERNS:
            if pattern in line:
                return line.strip()
    return None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Check captured stderr for error patterns after each test."""
    outcome = yield
    report = outcome.get_result()

    # Only check after the test call phase (not setup/teardown)
    if call.when == "call" and report.passed:
        # Check captured output sections
        for section_name, content in report.sections:
            if "stderr" in section_name.lower() or "captured" in section_name.lower():
                error_line = _contains_error(content)
                if error_line:
                    report.outcome = "failed"
                    report.longrepr = f"Error detected in captured output:\n{error_line}"
                    return


# Mocks


@dataclass
class GlobalMocks:
    hyprevt: tuple[MockReader, MockWriter] = None
    pyprctrl: tuple[MockReader, MockWriter] = None
    subprocess_call: MagicMock = None
    hyprctl: AsyncMock = None

    json_commands_result: dict[str, list | dict] = field(default_factory=dict)

    _pypr_command_reader: Callable = None

    # Test-only instance tracking (replaces Pyprland.instance singleton)
    pyprland_instance: Pyprland | None = None

    def reset(self):
        """Resets not standard mocks."""
        self.json_commands_result.clear()
        self.pyprland_instance = None

    async def pypr(self, cmd):
        """Simulates the pypr command."""
        assert self.pyprctrl
        await self.pyprctrl[0].q.put(b"%s\n" % cmd.encode("utf-8"))
        await self._pypr_command_reader(*self.pyprctrl)

    async def wait_queues(self):
        """Wait for all plugin queues to be empty.

        This ensures background tasks have finished processing.
        """
        if self.pyprland_instance is None:
            return
        for _ in range(100):  # max 10 seconds
            all_empty = all(q.empty() for q in self.pyprland_instance.queues.values())
            if all_empty:
                # Give one more tick for any pending task to complete
                await asyncio.sleep(0.01)
                return
            await asyncio.sleep(0.1)

    async def send_event(self, cmd):
        """Simulates receiving a Hyprland event."""
        assert self.hyprevt
        await self.hyprevt[0].q.put(b"%s\n" % cmd.encode("utf-8"))


mocks = GlobalMocks()


async def mocked_unix_server(command_reader, *_):
    mocks._pypr_command_reader = command_reader
    server = AsyncMock()
    server.close = Mock()
    return server


async def mocked_unix_connection(path):
    """Return a mocked reader & writer."""
    if path.endswith(".socket2.sock"):
        return mocks.hyprevt
    raise ValueError()


@fixture
async def empty_config(monkeypatch):
    """Runs with no config."""
    monkeypatch.setattr("tomllib.load", lambda x: {"pyprland": {"plugins": []}})
    yield


@fixture
async def third_monitor(monkeypatch):
    """Adds a third monitor."""
    MONITORS.append(EXTRA_MON)
    yield
    MONITORS[:] = MONITORS[:-1]


@fixture
async def sample1_config(monkeypatch):
    """Runs with config n°1."""
    monkeypatch.setattr("tomllib.load", lambda x: deepcopy(CONFIG_1))
    yield


async def mocked_hyprctl_json(self, command, *, log=None, **kwargs):
    if command in mocks.json_commands_result:
        return mocks.json_commands_result[command]
    if command.startswith("monitors"):
        return deepcopy(MONITORS)
    if command == "activeworkspace":
        return {"name": "1", "id": 1}
    if command == "version":
        return {
            "branch": "",
            "commit": "fe7b748eb668136dd0558b7c8279bfcd7ab4d759",
            "dirty": False,
            "commit_message": "props: bump version to 0.39.1",
            "commit_date": "Tue Apr 16 16:01:03 2024",
            "tag": "v0.39.1",
            "commits": 4460,
            "flags": [],
        }
    raise NotImplementedError()


@fixture
def subprocess_shell_mock(mocker):
    # Mocking the asyncio.create_subprocess_shell function
    mocked_subprocess_shell = mocker.patch("asyncio.create_subprocess_shell", name="mocked_shell_command")
    mocked_process = MagicMock(spec="subprocess.Process", name="mocked_subprocess")
    mocked_subprocess_shell.return_value = mocked_process
    mocked_process.pid = 1  # init always exists
    mocked_process.stderr = AsyncMock(return_code="")
    mocked_process.stdout = AsyncMock(return_code="")
    mocked_process.terminate = Mock()
    mocked_process.wait = AsyncMock()
    mocked_process.kill = Mock()
    mocked_process.return_code = 0
    return mocked_subprocess_shell, mocked_process


@fixture
async def server_fixture(monkeypatch, mocker):
    """Handle server setup boilerplate."""
    mocks.hyprctl = AsyncMock(return_value=True)
    mocks.hyprevt = (MockReader(), MockWriter())
    mocks.pyprctrl = (MockReader(), MockWriter())
    mocks.subprocess_call = MagicMock(return_value=0)

    monkeypatch.setenv("XDG_RUNTIME_DIR", "/tmp")
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "/tmp/will_not_be_used/")

    monkeypatch.setattr("asyncio.open_unix_connection", mocked_unix_connection)
    monkeypatch.setattr("asyncio.start_unix_server", mocked_unix_server)

    from pyprland.adapters.hyprland import HyprlandBackend

    monkeypatch.setattr(HyprlandBackend, "execute_json", mocked_hyprctl_json)
    monkeypatch.setattr(HyprlandBackend, "execute", mocks.hyprctl)

    from pyprland import ipc
    from pyprland.manager import Pyprland
    from pyprland.pypr_daemon import run_daemon

    # Capture the Pyprland instance when it's created
    original_init = Pyprland.__init__

    def patched_init(self):
        original_init(self)
        mocks.pyprland_instance = self

    monkeypatch.setattr(Pyprland, "__init__", patched_init)

    ipc.init()

    server_task = asyncio.create_task(run_daemon())

    # spy on Pyprland.run using mocker
    run_spi = mocker.spy(Pyprland, "run")

    for _ in range(10):
        if run_spi.call_count:
            break
        await asyncio.sleep(0.1)
    yield  # Run the test
    await mocks.hyprctl("exit")
    server_task.cancel()
    await asyncio.sleep(0.01)
    mocks.reset()


EXTRA_MON = {
    "id": 1,
    "name": "eDP-1",
    "description": "Sony (eDP-1)",
    "make": "Sony",
    "model": "XXX",
    "serial": "YYY",
    "width": 640,
    "height": 480,
    "refreshRate": 59.99900,
    "x": 0,
    "y": 0,
    "activeWorkspace": {"id": 2, "name": "2"},
    "specialWorkspace": {"id": 0, "name": ""},
    "reserved": [0, 50, 0, 0],
    "scale": 1.00,
    "transform": 0,
    "focused": True,
    "dpmsStatus": True,
    "vrr": False,
    "activelyTearing": False,
}

MONITORS = [
    {
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
        "activeWorkspace": {"id": 1, "name": "1"},
        "specialWorkspace": {"id": 0, "name": ""},
        "reserved": [0, 50, 0, 0],
        "scale": 1.00,
        "transform": 0,
        "focused": True,
        "dpmsStatus": True,
        "vrr": False,
        "activelyTearing": False,
    },
    {
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
        "activeWorkspace": {"id": 4, "name": "4"},
        "specialWorkspace": {"id": 0, "name": ""},
        "reserved": [0, 50, 0, 0],
        "scale": 1.00,
        "transform": 0,
        "focused": False,
        "dpmsStatus": True,
        "vrr": False,
        "activelyTearing": False,
    },
]
