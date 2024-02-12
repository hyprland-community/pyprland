import asyncio
from pytest_asyncio import fixture
from .conftest import mocks
from .testtools import wait_called
import pytest


@fixture
async def scratchpads(monkeypatch):
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
    yield


@pytest.mark.asyncio
async def test_not_found(scratchpads, subprocess_shell_mock, server_fixture):
    await mocks.pypr("toggle foobar")
    await wait_called(mocks.hyprctl)

    assert mocks.hyprctl.call_args[0][1] == "notify"


@pytest.mark.asyncio
async def test_std(scratchpads, subprocess_shell_mock, server_fixture):
    await mocks.pypr("toggle term")
    await wait_called(mocks.hyprctl)

    assert mocks.hyprctl.call_args[0][1] == "notify"
