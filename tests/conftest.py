" generic fixtures "
from unittest.mock import AsyncMock, Mock, MagicMock
from copy import deepcopy
import asyncio
from pytest_asyncio import fixture
import tomllib
import logging


def pytest_configure(config):
    from pyprland.common import init_logger

    init_logger("/dev/null", force_debug=True)


CONFIG_1 = tomllib.load(open("tests/sample_config.toml", "rb"))


class MockReader:
    "A StreamReader mock"

    def __init__(self):
        self.q = asyncio.Queue()

    async def readline(self, *a):
        return await self.q.get()

    read = readline


class MockWriter:
    "A StreamWriter mock"

    def __init__(self):
        self.write = Mock()
        self.drain = AsyncMock()
        self.close = Mock()
        self.wait_closed = AsyncMock()


# Mocks
hyprctl_mock: tuple[MockReader, MockWriter]
hyprevt_mock: tuple[MockReader, MockWriter]
pyprctrl_mock: tuple[MockReader, MockWriter]
subprocess_call: MagicMock
hyprctl_cmd: AsyncMock

misc_objects = {}


async def pypr(cmd):
    "Simulates the pypr command"
    assert pyprctrl_mock
    await pyprctrl_mock[0].q.put(b"%s\n" % cmd.encode("utf-8"))
    await misc_objects["pypr_command_reader"](*pyprctrl_mock)


async def my_mocked_unix_server(command_reader, *a):
    misc_objects["pypr_command_reader"] = command_reader
    mo = AsyncMock()
    mo.close = Mock()
    return mo


async def my_mocked_unix_connection(path):
    "Return a mocked reader & writer"
    if path.endswith(".socket.sock"):
        return hyprctl_mock
    if path.endswith(".socket2.sock"):
        return hyprevt_mock
    raise ValueError()


@fixture
async def empty_config(monkeypatch):
    "Runs with no config"
    monkeypatch.setattr("tomllib.load", lambda x: {"pyprland": {"plugins": []}})
    yield


@fixture
async def third_monitor(monkeypatch):
    "Adds a third monitor"
    MONITORS.append(EXTRA_MON)
    yield
    MONITORS[:] = MONITORS[:-1]


@fixture
async def sample1_config(monkeypatch):
    "Runs with config n°1"
    monkeypatch.setattr("tomllib.load", lambda x: deepcopy(CONFIG_1))
    yield


async def mocked_hyprctlJSON(command, logger=None):
    if command == "monitors":
        return deepcopy(MONITORS)
    raise NotImplementedError()


@fixture
async def server_fixture(monkeypatch):
    "Handle server setup boilerplate"
    global hyprevt_mock, hyprctl_mock, pyprctrl_mock, subprocess_call, hyprctl_cmd

    hyprctl_cmd = AsyncMock(return_value=True)
    hyprctl_mock = (MockReader(), MockWriter())
    hyprevt_mock = (MockReader(), MockWriter())
    pyprctrl_mock = (MockReader(), MockWriter())
    subprocess_call = MagicMock(return_value=0)

    monkeypatch.setenv("XDG_RUNTIME_DIR", "/tmp")
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "/tmp/will_not_be_used/")
    monkeypatch.setattr("pyprland.ipc.hyprctlJSON", mocked_hyprctlJSON)
    monkeypatch.setattr("pyprland.ipc.hyprctl", hyprctl_cmd)
    monkeypatch.setattr("subprocess.call", subprocess_call)

    from pyprland.command import run_daemon
    from pyprland import ipc

    monkeypatch.setattr("asyncio.open_unix_connection", my_mocked_unix_connection)
    monkeypatch.setattr("asyncio.start_unix_server", my_mocked_unix_server)

    ipc.init()

    # Use asyncio.gather to run the server logic concurrently with other async tasks
    server_task = asyncio.create_task(run_daemon())

    yield  # The test runs at this point
    await pypr("exit")
    server_task.cancel()
    await server_task

    # Cleanup: Cancel the server task to stop the server

    # Wait for the server task to complete


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
