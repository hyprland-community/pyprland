import sys
import tomllib

import pytest
from pytest_asyncio import fixture

from .conftest import mocks as tst

sys.path.append("sample_extension")


@fixture
async def external_plugin_config(monkeypatch):
    "external config"
    config = """
[pyprland]
plugins = ["pypr_examples.focus_counter"]
"""
    monkeypatch.setattr("tomllib.load", lambda x: tomllib.loads(config))
    yield


@pytest.mark.usefixtures("external_plugin_config", "server_fixture")
@pytest.mark.asyncio
async def test_ext_plugin():
    await tst.pypr("dummy")
    assert tst.hyprctl.call_count == 0, "No error notification should be emitted"
