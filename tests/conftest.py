" generic fixtures "
from typing import Callable
from unittest.mock import AsyncMock, Mock, MagicMock
from copy import deepcopy
import asyncio
from dataclasses import dataclass, field
from pytest_asyncio import fixture
import tomllib
from .testtools import MockReader, MockWriter

CONFIG_1 = tomllib.load(open("tests/sample_config.toml", "rb"))


def pytest_configure():
    "Runs once before all"
    from pyprland.common import init_logger

    init_logger("/dev/null", force_debug=True)


# Mocks


@dataclass
class GlobalMocks:
    hyprevt: tuple[MockReader, MockWriter] = None
    pyprctrl: tuple[MockReader, MockWriter] = None
    subprocess_call: MagicMock = None
    hyprctl: AsyncMock = None

    json_commands_result: dict[str, list | dict] = field(default_factory=dict)

    _pypr_command_reader: Callable = None

    def reset(self):
        "Resets not standard mocks"
        self.json_commands_result.clear()

    async def pypr(self, cmd):
        "Simulates the pypr command"
        assert self.pyprctrl
        await self.pyprctrl[0].q.put(b"%s\n" % cmd.encode("utf-8"))
        await self._pypr_command_reader(*self.pyprctrl)

    async def send_event(self, cmd):
        "Simulates receiving a Hyprland event"
        assert self.hyprevt
        await self.hyprevt[0].q.put(b"%s\n" % cmd.encode("utf-8"))


mocks = GlobalMocks()


async def mocked_unix_server(command_reader, *_):
    mocks._pypr_command_reader = command_reader
    server = AsyncMock()
    server.close = Mock()
    return server


async def mocked_unix_connection(path):
    "Return a mocked reader & writer"
    if path.endswith(".socket2.sock"):
        return mocks.hyprevt
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
    if command in mocks.json_commands_result:
        return mocks.json_commands_result[command]
    if command == "monitors":
        return deepcopy(MONITORS)
    if command == "activeworkspace":
        return {"name": "1", "id": 1}
    raise NotImplementedError()


@fixture
def subprocess_shell_mock(mocker):
    # Mocking the asyncio.create_subprocess_shell function
    mocked_subprocess_shell = mocker.patch(
        "asyncio.create_subprocess_shell", name="mocked_shell_command"
    )
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
    "Handle server setup boilerplate"
    mocks.hyprctl = AsyncMock(return_value=True)
    mocks.hyprevt = (MockReader(), MockWriter())
    mocks.pyprctrl = (MockReader(), MockWriter())
    mocks.subprocess_call = MagicMock(return_value=0)

    monkeypatch.setenv("XDG_RUNTIME_DIR", "/tmp")
    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "/tmp/will_not_be_used/")

    monkeypatch.setattr("asyncio.open_unix_connection", mocked_unix_connection)
    monkeypatch.setattr("asyncio.start_unix_server", mocked_unix_server)

    monkeypatch.setattr("pyprland.ipc.hyprctlJSON", mocked_hyprctlJSON)
    monkeypatch.setattr("pyprland.ipc.hyprctl", mocks.hyprctl)

    from pyprland.command import run_daemon
    from pyprland import ipc

    ipc.init()

    server_task = asyncio.create_task(run_daemon())
    from pyprland.command import Pyprland

    # spy on Pyprland.log.debug using mocker
    run_spi = mocker.spy(Pyprland, "run")

    for _ in range(10):
        if run_spi.call_count:
            break
        await asyncio.sleep(0.1)
    yield  # Run the test
    await mocks.hyprctl("exit")
    print("Closing mock server...")
    await mocks.pypr("exit")
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
