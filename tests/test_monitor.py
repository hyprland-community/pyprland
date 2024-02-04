import asyncio
import pytest
import tomllib
from . import conftest as tst

from pytest_asyncio import fixture


async def wait_called(fn, timeout=1.0):
    delay = 0.0
    while True:
        if fn.call_count:
            break
        await asyncio.sleep(0.02)
        delay += 0.02

        if delay > timeout:
            raise TimeoutError()


@fixture
async def descr_config(monkeypatch):
    "Runs with config n°1"
    config = """
[pyprland]
plugins = ["monitors"]

[monitors]
startup_relayout = false

[monitors.placement]
"Sony".rightOf = "Microstep"
"Microstep".rightOf = ["BenQ"]
    """
    monkeypatch.setattr("tomllib.load", lambda x: tomllib.loads(config))
    yield


@fixture
async def topdown_config(monkeypatch):
    "Runs with config n°1"
    config = """
[pyprland]
plugins = ["monitors"]

[monitors]
startup_relayout = false

[monitors.placement]
"(eDP-1)".topOf = "(DP-1)"
"(DP-1)".topOf = "(HDMI-A-1)"
    """
    monkeypatch.setattr("tomllib.load", lambda x: tomllib.loads(config))
    yield


@fixture
async def bottomup_config(monkeypatch):
    "Runs with config n°1"
    config = """
[pyprland]
plugins = ["monitors"]

[monitors]
startup_relayout = false

[monitors.placement]
"(eDP-1)".bottomOf = "(DP-1)"
"(DP-1)".bottomOf = "(HDMI-A-1)"
    """
    monkeypatch.setattr("tomllib.load", lambda x: tomllib.loads(config))
    yield


def get_xrandr_calls():
    return {tuple(al[0][0]) for al in tst.subprocess_call.call_args_list}


@fixture
async def reversed_config(monkeypatch):
    "Runs with config n°1"
    config = """
[pyprland]
plugins = ["monitors"]

[monitors]
startup_relayout = false

[monitors.placement]
"(eDP-1)".leftOf = "(DP-1)"
"(DP-1)".leftOf = "(HDMI-A-1)"
    """
    monkeypatch.setattr("tomllib.load", lambda x: tomllib.loads(config))
    yield


@pytest.mark.usefixtures("sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_relayout():
    await tst.pypr("relayout")
    await wait_called(tst.subprocess_call)
    calls = get_xrandr_calls()
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
    await tst.pypr("relayout")
    await wait_called(tst.subprocess_call)
    calls = get_xrandr_calls()
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


@pytest.mark.usefixtures("third_monitor", "bottomup_config", "server_fixture")
@pytest.mark.asyncio
async def test_3screens_relayout_b():
    await tst.pypr("relayout")
    await wait_called(tst.subprocess_call)
    calls = get_xrandr_calls()
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
            "0,1080",
            "--output",
            "eDP-1",
            "--pos",
            "0,2520",
        )
    )


@pytest.mark.usefixtures("third_monitor", "reversed_config", "server_fixture")
@pytest.mark.asyncio
async def test_3screens_rev_relayout():
    await tst.pypr("relayout")
    await wait_called(tst.subprocess_call)
    calls = get_xrandr_calls()
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


@pytest.mark.usefixtures("sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_events():
    await tst.send_event("monitoradded>>DP-1")
    await wait_called(tst.subprocess_call)
    calls = get_xrandr_calls()
    print(calls)
    calls.remove(
        (
            "wlr-randr",
            "--output",
            "DP-1",
            "--pos",
            "1920,0",
        )
    )


@pytest.mark.usefixtures("descr_config", "server_fixture")
@pytest.mark.asyncio
async def test_events_d():
    await tst.send_event("monitoradded>>DP-1")
    await wait_called(tst.subprocess_call)
    calls = get_xrandr_calls()
    print(calls)
    calls.remove(
        (
            "wlr-randr",
            "--output",
            "DP-1",
            "--pos",
            "1920,0",
        )
    )


@pytest.mark.usefixtures("reversed_config", "server_fixture")
@pytest.mark.asyncio
async def test_events2():
    await tst.send_event("monitoradded>>DP-1")
    await wait_called(tst.subprocess_call)
    calls = get_xrandr_calls()
    print(calls)
    calls.remove(("wlr-randr", "--output", "DP-1", "--pos", "-3440,0"))


@pytest.mark.usefixtures("topdown_config", "server_fixture")
@pytest.mark.asyncio
async def test_events3():
    await tst.send_event("monitoradded>>DP-1")
    await wait_called(tst.subprocess_call)
    calls = get_xrandr_calls()
    print(calls)
    calls.remove(("wlr-randr", "--output", "DP-1", "--pos", "0,-1440"))


@pytest.mark.usefixtures("sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_events3b():
    await tst.send_event("monitoradded>>HDMI-A-1")
    await wait_called(tst.subprocess_call)
    calls = get_xrandr_calls()
    print(calls)
    calls.remove(("wlr-randr", "--output", "HDMI-A-1", "--pos", "-1920,0"))


@pytest.mark.usefixtures("bottomup_config", "server_fixture")
@pytest.mark.asyncio
async def test_events4():
    await tst.send_event("monitoradded>>DP-1")
    await wait_called(tst.subprocess_call)
    calls = get_xrandr_calls()
    print(calls)
    calls.remove(("wlr-randr", "--output", "DP-1", "--pos", "0,1080"))


@pytest.mark.usefixtures("empty_config", "server_fixture")
@pytest.mark.asyncio
async def test_nothing():
    await tst.pypr("inexistant")
    assert tst.hyprctl.call_args_list[0][0][1] == "notify"
    assert tst.hyprctl.call_count == 1
