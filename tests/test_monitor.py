import asyncio
import pytest
from . import conftest as tst


@pytest.mark.usefixtures("sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_relayout():
    await tst.pyprctrl_mock.q.put(b"relayout\n")
    assert tst.subprocess_call.call_count == 1
    calls = set([tuple(al[0][0]) for al in tst.subprocess_call.call_args_list])
    calls.remove(tuple(("wlr-randr", "--output", "DP-1", "--pos", "1920,0")))


@pytest.mark.skip(reason="Only two monitors are currently supported")
@pytest.mark.usefixtures("third_monitor", "sample1_config", "server_fixture")
@pytest.mark.asyncio
async def test_broken_relayout():
    await tst.pyprctrl_mock.q.put(b"relayout\n")
    assert tst.subprocess_call.call_count == 1
    calls = set([tuple(al[0][0]) for al in tst.subprocess_call.call_args_list])
    calls.remove(tuple(("wlr-randr", "--output", "DP-1", "--pos", "1920,0")))
    calls.remove(tuple(("wlr-randr", "--output", "eDP-1", "--pos", "5360,0")))


@pytest.mark.usefixtures("empty_config", "server_fixture")
@pytest.mark.asyncio
async def test_nothing():
    await tst.pyprctrl_mock.q.put(b"relayout\n")
    assert tst.subprocess_call.call_count == 0
