from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
import tomllib

from .conftest import mocks as tst
from .testtools import wait_called

from pyprland.manager import Pyprland


@pytest.mark.usefixtures("sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_reload(monkeypatch):
    config = """
[pyprland]
plugins = ["monitors"]

[monitors]
startup_relayout = true
placement = {}
"""
    master = cast(Pyprland, tst.pyprland_instance)
    cfg = master.plugins["monitors"].config

    placement = cfg["placement"]
    bool_opt = cfg["startup_relayout"]

    load_proxy = Mock(wraps=lambda x: tomllib.loads(config))

    # Wrap the plugin's load_config to detect when config is updated
    original_load_config = master.plugins["monitors"].load_config
    load_config_proxy = AsyncMock(wraps=original_load_config)
    master.plugins["monitors"].load_config = load_config_proxy

    monkeypatch.setattr("tomllib.load", load_proxy)
    await tst.pypr("reload")

    await wait_called(load_config_proxy)

    assert placement is cfg["placement"]
    assert bool_opt != cfg["startup_relayout"]
    assert cfg["startup_relayout"] is True
    assert cfg["placement"] == {}
