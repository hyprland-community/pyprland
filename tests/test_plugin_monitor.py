import tomllib

import pytest
from pytest_asyncio import fixture

from .conftest import mocks as tst
from .testtools import wait_called


@fixture
async def shapeL_config(monkeypatch):
    "L shape"
    config = """
[pyprland]
plugins = ["monitors"]

[monitors]
startup_relayout = false
new_monitor_delay = 0

[monitors.placement]
"Sony".topOf = ["BenQ"]
"Microstep".rightOf = ["BenQ"]
    """
    monkeypatch.setattr("tomllib.load", lambda x: tomllib.loads(config))
    yield


@fixture
async def flipped_shapeL_config(monkeypatch):
    "flipped L shape"
    config = """
[pyprland]
plugins = ["monitors"]

[monitors]
startup_relayout = false
new_monitor_delay = 0

[monitors.placement]
"Sony".bottomOf = "BenQ"
"Microstep".rightOf = "Sony"
    """
    monkeypatch.setattr("tomllib.load", lambda x: tomllib.loads(config))
    yield


@fixture
async def descr_config(monkeypatch):
    "Runs with config n°1"
    config = """
[pyprland]
plugins = ["monitors"]

[monitors]
startup_relayout = false
new_monitor_delay = 0

[monitors.placement]
"Sony".rightCenterOf = "Microstep"
"Microstep".rightCenterOf = ["BenQ"]
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
new_monitor_delay = 0

[monitors.placement]
"eDP-1".topOf = "DP-1"
"DP-1".topOf = "HDMI-A-1"
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
new_monitor_delay = 0

[monitors.placement]
"eDP-1".bottomCenterOf = "DP-1"
"DP-1".bottomCenterOf = "HDMI-A-1"
    """
    monkeypatch.setattr("tomllib.load", lambda x: tomllib.loads(config))
    yield


def get_xrandr_calls(mock):
    return {al[0][0] for al in mock.call_args_list}


@fixture
async def reversed_config(monkeypatch):
    "Runs with config n°1"
    config = """
[pyprland]
plugins = ["monitors"]

[monitors]
startup_relayout = false
new_monitor_delay = 0

[monitors.placement]
"eDP-1".leftOf = "DP-1"
"DP-1".leftOf = "HDMI-A-1"
    """
    monkeypatch.setattr("tomllib.load", lambda x: tomllib.loads(config))
    yield


def assert_modes(call_list, expected=[], allow_empty=False):
    ref_str = {x[0][0] for x in call_list}
    for e in expected:
        ref_str.remove(e)

    if not allow_empty:
        assert len(list(ref_str)) == 0


@pytest.mark.usefixtures("sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_relayout():
    await tst.pypr("relayout")
    await wait_called(tst.hyprctl)
    assert_modes(
        tst.hyprctl.call_args_list,
        [
            "monitor HDMI-A-1,1920x1080@60.0,0x0,1.0,transform,0",
            "monitor DP-1,3440x1440@59.999,1920x0,1.0,transform,0",
        ],
    )


@pytest.mark.usefixtures("third_monitor", "sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_3screens_relayout():
    await tst.pypr("relayout")
    await wait_called(tst.hyprctl)
    assert_modes(
        tst.hyprctl.call_args_list,
        [
            "monitor HDMI-A-1,1920x1080@60.0,0x0,1.0,transform,0",
            "monitor DP-1,3440x1440@59.999,1920x0,1.0,transform,0",
            "monitor eDP-1,640x480@59.999,5360x0,1.0,transform,0",
        ],
    )


@pytest.mark.usefixtures("third_monitor", "bottomup_config", "server_fixture")
@pytest.mark.asyncio
async def test_3screens_relayout_b():
    await tst.pypr("relayout")
    await wait_called(tst.hyprctl)
    assert_modes(
        tst.hyprctl.call_args_list,
        [
            "monitor HDMI-A-1,1920x1080@60.0,760x0,1.0,transform,0",
            "monitor DP-1,3440x1440@59.999,0x1080,1.0,transform,0",
            "monitor eDP-1,640x480@59.999,1400x2520,1.0,transform,0",
        ],
    )


@pytest.mark.usefixtures("third_monitor", "shapeL_config", "server_fixture")
@pytest.mark.asyncio
async def test_shape_l():
    await tst.pypr("relayout")
    await wait_called(tst.hyprctl)
    assert_modes(
        tst.hyprctl.call_args_list,
        [
            "monitor HDMI-A-1,1920x1080@60.0,0x480,1.0,transform,0",
            "monitor DP-1,3440x1440@59.999,1920x480,1.0,transform,0",
            "monitor eDP-1,640x480@59.999,0x0,1.0,transform,0",
        ],
    )


@pytest.mark.usefixtures("third_monitor", "flipped_shapeL_config", "server_fixture")
@pytest.mark.asyncio
async def test_flipped_shape_l():
    await tst.pypr("relayout")
    await wait_called(tst.hyprctl)
    assert_modes(
        tst.hyprctl.call_args_list,
        [
            "monitor HDMI-A-1,1920x1080@60.0,0x0,1.0,transform,0",
            "monitor DP-1,3440x1440@59.999,640x1080,1.0,transform,0",
            "monitor eDP-1,640x480@59.999,0x1080,1.0,transform,0",
        ],
    )


@pytest.mark.usefixtures("third_monitor", "reversed_config", "server_fixture")
@pytest.mark.asyncio
async def test_3screens_rev_relayout():
    await tst.pypr("relayout")
    await wait_called(tst.hyprctl)
    assert_modes(
        tst.hyprctl.call_args_list,
        [
            "monitor HDMI-A-1,1920x1080@60.0,4080x0,1.0,transform,0",
            "monitor DP-1,3440x1440@59.999,640x0,1.0,transform,0",
            "monitor eDP-1,640x480@59.999,0x0,1.0,transform,0",
        ],
    )


@pytest.mark.usefixtures("sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_events():
    await tst.send_event("monitoradded>>DP-1")
    await wait_called(tst.hyprctl)
    assert_modes(
        tst.hyprctl.call_args_list,
        [
            "monitor HDMI-A-1,1920x1080@60.0,0x0,1.0,transform,0",
            "monitor DP-1,3440x1440@59.999,1920x0,1.0,transform,0",
        ],
    )


@pytest.mark.usefixtures("descr_config", "server_fixture")
@pytest.mark.asyncio
async def test_events_d():
    await tst.send_event("monitoradded>>DP-1")
    await wait_called(tst.hyprctl)

    assert_modes(
        tst.hyprctl.call_args_list,
        [
            "monitor HDMI-A-1,1920x1080@60.0,0x180,1.0,transform,0",
            "monitor DP-1,3440x1440@59.999,1920x0,1.0,transform,0",
        ],
    )


@pytest.mark.usefixtures("reversed_config", "server_fixture")
@pytest.mark.asyncio
async def test_events2():
    await tst.send_event("monitoradded>>DP-1")

    await wait_called(tst.hyprctl)

    assert_modes(
        tst.hyprctl.call_args_list,
        [
            "monitor HDMI-A-1,1920x1080@60.0,3440x0,1.0,transform,0",
            "monitor DP-1,3440x1440@59.999,0x0,1.0,transform,0",
        ],
    )


@pytest.mark.usefixtures("topdown_config", "server_fixture")
@pytest.mark.asyncio
async def test_events3():
    await tst.send_event("monitoradded>>DP-1")

    await wait_called(tst.hyprctl)

    assert_modes(
        tst.hyprctl.call_args_list,
        [
            "monitor HDMI-A-1,1920x1080@60.0,0x1440,1.0,transform,0",
            "monitor DP-1,3440x1440@59.999,0x0,1.0,transform,0",
        ],
    )


@pytest.mark.usefixtures("sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_events3b():
    await tst.send_event("monitoradded>>HDMI-A-1")

    await wait_called(tst.hyprctl)

    assert_modes(
        tst.hyprctl.call_args_list,
        [
            "monitor HDMI-A-1,1920x1080@60.0,0x0,1.0,transform,0",
            "monitor DP-1,3440x1440@59.999,1920x0,1.0,transform,0",
        ],
    )


@pytest.mark.usefixtures("bottomup_config", "server_fixture")
@pytest.mark.asyncio
async def test_events4():
    await tst.send_event("monitoradded>>DP-1")

    await wait_called(tst.hyprctl)

    assert_modes(
        tst.hyprctl.call_args_list,
        [
            "monitor HDMI-A-1,1920x1080@60.0,760x0,1.0,transform,0",
            "monitor DP-1,3440x1440@59.999,0x1080,1.0,transform,0",
        ],
    )


@pytest.mark.usefixtures("empty_config", "server_fixture")
@pytest.mark.asyncio
async def test_nothing():
    await tst.pypr("inexistant")
    assert tst.hyprctl.call_args_list[0][0][1] == "notify"
    assert tst.hyprctl.call_count == 1
