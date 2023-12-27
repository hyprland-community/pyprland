" generic fixtures "
from unittest.mock import AsyncMock, Mock
import asyncio
import pytest
from pytest_asyncio import fixture
import tomllib

import logging

logging.basicConfig(level=logging.DEBUG)

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


orig_start_unix_server = asyncio.start_unix_server

hyprctl_mock = (MockReader(), MockWriter())
hyprevt_mock = (MockReader(), MockWriter())

pyprctrl_mock = MockReader()

misc_objects = {}


async def my_mocked_unix_server(reader, *a):
    misc_objects["control"] = reader
    mo = AsyncMock()
    mo.close = Mock()
    return mo


async def my_mocked_unix_connection(path):
    "Return a mocked reader & writer"
    if path.endswith(".socket.sock"):
        return hyprctl_mock
    elif path.endswith(".socket2.sock"):
        return hyprevt_mock
    else:
        raise ValueError()


@fixture
async def empty_config(monkeypatch):
    "Runs with no config"
    monkeypatch.setattr("tomllib.load", lambda x: {"pyprland": {"plugins": []}})
    yield


@fixture
async def sample1_config(monkeypatch):
    "Runs with no config"
    monkeypatch.setattr("tomllib.load", lambda x: CONFIG_1)
    yield


@fixture
async def server_fixture(monkeypatch):
    "Handle server setup boilerplate"
    orig_open_unix_connection = asyncio.open_unix_connection
    asyncio.open_unix_connection = my_mocked_unix_connection
    asyncio.start_unix_server = my_mocked_unix_server

    monkeypatch.setenv("HYPRLAND_INSTANCE_SIGNATURE", "/tmp/will_not_be_used/")
    from pyprland.command import run_daemon
    from pyprland.ipc import init as ipc_init

    ipc_init()

    # Use asyncio.gather to run the server logic concurrently with other async tasks
    server_task = asyncio.create_task(run_daemon())

    # Allow some time for the server to initialize
    await asyncio.sleep(0.5)  # Adjust the duration as needed

    yield  # The test runs at this point

    # Cleanup: Cancel the server task to stop the server
    server_task.cancel()

    asyncio.open_unix_connection = orig_open_unix_connection
    asyncio.start_unix_server = orig_start_unix_server

    # Wait for the server task to complete
    await server_task
