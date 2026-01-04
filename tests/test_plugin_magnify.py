import pytest
from pytest_asyncio import fixture

from .conftest import mocks
from .testtools import wait_called


@fixture
async def magnify_config(monkeypatch):
    d = {"pyprland": {"plugins": ["magnify"]}, "magnify": {"factor": 2.0}}
    monkeypatch.setattr("tomllib.load", lambda x: d)
    yield


@pytest.mark.asyncio
async def test_magnify(magnify_config, server_fixture):
    # Test enabling zoom (default factor 2.0)
    await mocks.pypr("zoom")
    await wait_called(mocks.hyprctl)

    # Check if hyprctl was called.
    # Note: The actual keyword might be "misc:cursor_zoom_factor" or "cursor:zoom_factor"
    # depending on the mocked version state, but we can check if it ends with the correct value.
    cmd = mocks.hyprctl.call_args[0][0]
    assert "zoom_factor 2.0" in cmd

    # Test toggling off (reset to 1)
    await mocks.pypr("zoom")
    await wait_called(mocks.hyprctl, count=2)
    cmd = mocks.hyprctl.call_args[0][0]
    assert "zoom_factor 1.0" in cmd

    # Test specific factor
    await mocks.pypr("zoom 3")
    await wait_called(mocks.hyprctl, count=3)
    cmd = mocks.hyprctl.call_args[0][0]
    assert "zoom_factor 3.0" in cmd
