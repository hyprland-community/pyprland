import sys

import pytest
import tomllib
from pytest_asyncio import fixture

from .conftest import mocks as tst

sys.path.append("sample_extension")


@fixture
async def external_plugin_config(monkeypatch):
    """External config."""
    config = """
[pyprland]
plugins = ["pypr_examples.focus_counter"]
"""
    monkeypatch.setattr("tomllib.load", lambda x: tomllib.loads(config))
    yield


@pytest.mark.usefixtures("external_plugin_config", "server_fixture")
@pytest.mark.asyncio
async def test_ext_plugin():
    await tst.pypr("counter")
    await tst.wait_queues()
    # The plugin should successfully call notify_info, which invokes hyprctl
    assert tst.hyprctl.call_count == 1, "notify_info should be called once"
    # Check that the notification was an info notification (not an error)
    call_args = tst.hyprctl.call_args[0][0]
    assert "Focus changed" in call_args, "Should contain focus change message"
