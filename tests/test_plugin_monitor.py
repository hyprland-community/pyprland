import pytest
import tomllib
from .conftest import mocks as tst
from .testtools import wait_called

from pytest_asyncio import fixture


@fixture
async def shapeL_config(monkeypatch):
    "L shape"
    config = """
[pyprland]
plugins = ["monitors"]

[monitors]
startup_relayout = false

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

[monitors.placement]
"(eDP-1)".leftOf = "(DP-1)"
"(DP-1)".leftOf = "(HDMI-A-1)"
    """
    monkeypatch.setattr("tomllib.load", lambda x: tomllib.loads(config))
    yield


@pytest.mark.usefixtures("sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_relayout(subprocess_shell_mock):
    mocked_subprocess_shell, mocked_process = subprocess_shell_mock
    await tst.pypr("relayout")
    await wait_called(mocked_subprocess_shell)
    calls = get_xrandr_calls(mocked_subprocess_shell)

    calls.remove("wlr-randr --output HDMI-A-1 --pos 0,0 --output DP-1 --pos 1920,0")


@pytest.mark.usefixtures("third_monitor", "sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_3screens_relayout(subprocess_shell_mock):
    mocked_subprocess_shell, mocked_process = subprocess_shell_mock
    await tst.pypr("relayout")
    await wait_called(mocked_subprocess_shell)
    calls = get_xrandr_calls(mocked_subprocess_shell)

    calls.remove(
        "wlr-randr --output HDMI-A-1 --pos 0,0 --output DP-1 --pos 1920,0 --output eDP-1 --pos 5360,0"
    )


@pytest.mark.usefixtures("third_monitor", "bottomup_config", "server_fixture")
@pytest.mark.asyncio
async def test_3screens_relayout_b(subprocess_shell_mock):
    mocked_subprocess_shell, mocked_process = subprocess_shell_mock
    await tst.pypr("relayout")
    await wait_called(mocked_subprocess_shell)
    calls = get_xrandr_calls(mocked_subprocess_shell)
    calls.remove(
        "wlr-randr --output HDMI-A-1 --pos 0,0 --output DP-1 --pos 0,1080 --output eDP-1 --pos 0,2520"
    )


@pytest.mark.usefixtures("third_monitor", "shapeL_config", "server_fixture")
@pytest.mark.asyncio
async def test_shape_l(subprocess_shell_mock):
    mocked_subprocess_shell, mocked_process = subprocess_shell_mock
    await tst.pypr("relayout")
    await wait_called(mocked_subprocess_shell)
    calls = get_xrandr_calls(mocked_subprocess_shell)

    calls.remove(
        "wlr-randr --output eDP-1 --pos 0,0 --output HDMI-A-1 --pos 0,480 --output DP-1 --pos 1920,480"
    )


@pytest.mark.usefixtures("third_monitor", "flipped_shapeL_config", "server_fixture")
@pytest.mark.asyncio
async def test_flipped_shape_l(subprocess_shell_mock):
    mocked_subprocess_shell, mocked_process = subprocess_shell_mock
    await tst.pypr("relayout")
    await wait_called(mocked_subprocess_shell)
    calls = get_xrandr_calls(mocked_subprocess_shell)

    calls.remove(
        "wlr-randr --output HDMI-A-1 --pos 0,0 --output eDP-1 --pos 0,1080 --output DP-1 --pos 640,1080"
    )


@pytest.mark.usefixtures("third_monitor", "reversed_config", "server_fixture")
@pytest.mark.asyncio
async def test_3screens_rev_relayout(subprocess_shell_mock):
    mocked_subprocess_shell, mocked_process = subprocess_shell_mock
    await tst.pypr("relayout")
    await wait_called(mocked_subprocess_shell)
    calls = get_xrandr_calls(mocked_subprocess_shell)

    calls.remove(
        "wlr-randr --output eDP-1 --pos 0,0 --output DP-1 --pos 640,0 --output HDMI-A-1 --pos 4080,0"
    )


@pytest.mark.usefixtures("sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_events(subprocess_shell_mock):
    await tst.send_event("monitoradded>>DP-1")
    await wait_called(subprocess_shell_mock[0])
    calls = get_xrandr_calls(subprocess_shell_mock[0])
    print(calls)
    calls.remove("wlr-randr --output DP-1 --pos 1920,0")


@pytest.mark.usefixtures("descr_config", "server_fixture")
@pytest.mark.asyncio
async def test_events_d(subprocess_shell_mock):
    await tst.send_event("monitoradded>>DP-1")
    await wait_called(subprocess_shell_mock[0])
    calls = get_xrandr_calls(subprocess_shell_mock[0])
    print(calls)
    calls.remove("wlr-randr --output DP-1 --pos 1920,-180")


@pytest.mark.usefixtures("reversed_config", "server_fixture")
@pytest.mark.asyncio
async def test_events2(subprocess_shell_mock):
    await tst.send_event("monitoradded>>DP-1")
    await wait_called(subprocess_shell_mock[0])
    calls = get_xrandr_calls(subprocess_shell_mock[0])
    print(calls)
    calls.remove("wlr-randr --output DP-1 --pos -3440,0")


@pytest.mark.usefixtures("topdown_config", "server_fixture")
@pytest.mark.asyncio
async def test_events3(subprocess_shell_mock):
    await tst.send_event("monitoradded>>DP-1")
    await wait_called(subprocess_shell_mock[0])
    calls = get_xrandr_calls(subprocess_shell_mock[0])
    print(calls)
    calls.remove("wlr-randr --output DP-1 --pos 0,-1440")


@pytest.mark.usefixtures("sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_events3b(subprocess_shell_mock):
    await tst.send_event("monitoradded>>HDMI-A-1")
    await wait_called(subprocess_shell_mock[0])
    calls = get_xrandr_calls(subprocess_shell_mock[0])
    print(calls)
    calls.remove("wlr-randr --output HDMI-A-1 --pos -1920,0")


@pytest.mark.usefixtures("bottomup_config", "server_fixture")
@pytest.mark.asyncio
async def test_events4(subprocess_shell_mock):
    await tst.send_event("monitoradded>>DP-1")
    await wait_called(subprocess_shell_mock[0])
    calls = get_xrandr_calls(subprocess_shell_mock[0])
    print(calls)
    calls.remove("wlr-randr --output DP-1 --pos 0,1080")


@pytest.mark.usefixtures("empty_config", "server_fixture")
@pytest.mark.asyncio
async def test_nothing():
    await tst.pypr("inexistant")
    assert tst.hyprctl.call_args_list[0][0][1] == "notify"
    assert tst.hyprctl.call_count == 1
