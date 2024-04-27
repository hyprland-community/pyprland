import asyncio

import pytest
from pytest_asyncio import fixture

from .conftest import mocks
from .testtools import wait_called


@fixture
async def dpms_config(monkeypatch):
    d = {"pyprland": {"plugins": ["toggle_dpms"]}}
    monkeypatch.setattr("tomllib.load", lambda x: d)
    yield


@pytest.mark.asyncio
async def test_dpms(dpms_config, server_fixture):
    await mocks.pypr("toggle_dpms")
    await wait_called(mocks.hyprctl)
    assert mocks.hyprctl.call_args[0][0] == "dpms off"
