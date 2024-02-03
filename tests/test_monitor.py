import asyncio
import pytest
import tomllib
from . import conftest as tst

from pytest_asyncio import fixture


@fixture
async def reversed_config(monkeypatch):
    "Runs with config n°1"
    config = """
[pyprland]
plugins = ["monitors"]

[monitors.placement]
"(eDP-1)".leftOf = "(DP-1)"
"(DP-1)".leftOf = "(HDMI-A-1)"
    """
    monkeypatch.setattr("tomllib.load", lambda x: tomllib.loads(config))
    yield


@pytest.mark.usefixtures("sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_relayout():
    await tst.pyprctrl_mock.q.put(b"relayout\n")
    assert tst.subprocess_call.call_count == 1
    calls = set([tuple(al[0][0]) for al in tst.subprocess_call.call_args_list])
    calls.remove(
        (
            "wlr-randr",
            "--output",
            "HDMI-A-1",
            "--pos",
            "0,0",
            "--output",
            "DP-1",
            "--pos",
            "1920,0",
        )
    )


@pytest.mark.usefixtures("third_monitor", "sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_3screens_relayout():
    await tst.pyprctrl_mock.q.put(b"relayout\n")
    assert tst.subprocess_call.call_count == 1
    calls = set([tuple(al[0][0]) for al in tst.subprocess_call.call_args_list])
    print(calls)
    calls.remove(
        (
            "wlr-randr",
            "--output",
            "HDMI-A-1",
            "--pos",
            "0,0",
            "--output",
            "DP-1",
            "--pos",
            "1920,0",
            "--output",
            "eDP-1",
            "--pos",
            "5360,0",
        )
    )


@pytest.mark.usefixtures("third_monitor", "reversed_config", "server_fixture")
@pytest.mark.asyncio
async def test_3screens_relayout():
    await tst.pyprctrl_mock.q.put(b"relayout\n")
    assert tst.subprocess_call.call_count == 1
    calls = set([tuple(al[0][0]) for al in tst.subprocess_call.call_args_list])
    print(calls)
    calls.remove(
        (
            "wlr-randr",
            "--output",
            "eDP-1",
            "--pos",
            "0,0",
            "--output",
            "DP-1",
            "--pos",
            "640,0",
            "--output",
            "HDMI-A-1",
            "--pos",
            "4080,0",
        )
    )


@pytest.mark.usefixtures("empty_config", "server_fixture")
@pytest.mark.asyncio
async def test_nothing():
    await tst.pyprctrl_mock.q.put(b"relayout\n")
    assert tst.subprocess_call.call_count == 0
