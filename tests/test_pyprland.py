import asyncio
import tomllib
from typing import cast
from unittest.mock import Mock

import pytest

from .conftest import mocks as tst
from .testtools import wait_called


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
    from pyprland.command import Pyprland

    master = cast(Pyprland, Pyprland.instance)
    cfg = master.plugins["monitors"].config

    placement = cfg["placement"]
    bool_opt = cfg["startup_relayout"]

    load_proxy = Mock(wraps=lambda x: tomllib.loads(config))

    monkeypatch.setattr("tomllib.load", load_proxy)
    await tst.pypr("reload")

    await wait_called(load_proxy)
    # FIXME: find a method call to wait
    await asyncio.sleep(0.1)

    assert placement != cfg["placement"]
    assert bool_opt != cfg["startup_relayout"]
    assert cfg["startup_relayout"] == True
    assert cfg["placement"] == {}
