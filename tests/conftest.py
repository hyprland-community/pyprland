" generic fixtures "
import typing
from unittest.mock import AsyncMock, Mock, MagicMock
from copy import deepcopy
import asyncio
from dataclasses import dataclass
from pytest_asyncio import fixture
import tomllib
from .testtools import MockReader, MockWriter

CONFIG_1 = tomllib.load(open("tests/sample_config.toml", "rb"))


@dataclass
class Obj:
    "keep track of pypr's object when needed"
    pypr_command_reader: typing.Callable = lambda *a: None


def pytest_configure():
    "Runs once before all"
    from pyprland.common import init_logger

    init_logger("/dev/null", force_debug=True)


# Mocks
hyprevt: tuple[MockReader, MockWriter]
pyprctrl: tuple[MockReader, MockWriter]
subprocess_call: MagicMock
hyprctl: AsyncMock
misc_objects = Obj()


async def pypr(cmd):
    "Simulates the pypr command"
    assert pyprctrl
    await pyprctrl[0].q.put(b"%s\n" % cmd.encode("utf-8"))
    await misc_objects.pypr_command_reader(*pyprctrl)


async def send_event(cmd):
    "Simulates receiving a Hyprland event"
    assert hyprevt
    await hyprevt[0].q.put(b"%s\n" % cmd.encode("utf-8"))


async def mocked_unix_server(command_reader, *a):
    misc_objects.pypr_command_reader = command_reader
    server = AsyncMock()
    server.close = Mock()
    return server


async def mocked_unix_connection(path):
    "Return a mocked reader & writer"
    if path.endswith(".socket2.sock"):
        return hyprevt
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
    if command == "activeworkspace":
        return {"name": "1", "id": 1}
    if command == "activewindow":
        return {"address": "0x1234567890"}
    raise NotImplementedError()


@fixture
def subprocess_shell_mock(mocker):
    # Mocking the asyncio.create_subprocess_shell function
    mocked_subprocess_shell = mocker.patch("asyncio.create_subprocess_shell")
    mocked_process = MagicMock(spec=asyncio.subprocess.Process)
    mocked_subprocess_shell.return_value = mocked_process
    return mocked_subprocess_shell, mocked_process


@fixture
async def server_fixture(monkeypatch):
    "Handle server setup boilerplate"
    global hyprevt, pyprctrl, subprocess_call, hyprctl

    hyprctl = AsyncMock(return_value=True)
    hyprevt = (MockReader(), MockWriter())
    pyprctrl = (MockReader(), MockWriter())
    subprocess_call = MagicMock(return_value=0)

    monkeypatch.setenv("XDG_RUNTIME_DIR", "/tmp")
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "/tmp/will_not_be_used/")

    monkeypatch.setattr("asyncio.open_unix_connection", mocked_unix_connection)
    monkeypatch.setattr("asyncio.start_unix_server", mocked_unix_server)

    monkeypatch.setattr("pyprland.ipc.hyprctlJSON", mocked_hyprctlJSON)
    monkeypatch.setattr("pyprland.ipc.hyprctl", hyprctl)

    monkeypatch.setattr("subprocess.call", subprocess_call)

    from pyprland.command import run_daemon
    from pyprland import ipc

    ipc.init()

    server_task = asyncio.create_task(run_daemon())
    from pyprland.command import Pyprland

    for _ in range(10):
        if Pyprland.instance and Pyprland.instance.initialized:
            break
        await asyncio.sleep(0.1)
    yield  # Run the test
    Pyprland.instance.initialized = False
    server_task.cancel()
    await server_task


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
