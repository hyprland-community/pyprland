#!/bin/env python
import asyncio
from typing import Any
import json
import os

from .common import DEBUG


HYPRCTL = f'/tmp/hypr/{ os.environ["HYPRLAND_INSTANCE_SIGNATURE"] }/.socket.sock'
EVENTS = f'/tmp/hypr/{ os.environ["HYPRLAND_INSTANCE_SIGNATURE"] }/.socket2.sock'


async def get_event_stream():
    return await asyncio.open_unix_connection(EVENTS)


async def hyprctlJSON(command) -> list[dict[str, Any]] | dict[str, Any]:
    """Run an IPC command and return the JSON output."""
    if DEBUG:
        print("(JS)>>>", command)
    ctl_reader, ctl_writer = await asyncio.open_unix_connection(HYPRCTL)
    ctl_writer.write(f"-j/{command}".encode())
    await ctl_writer.drain()
    resp = await ctl_reader.read()
    ctl_writer.close()
    await ctl_writer.wait_closed()
    ret = json.loads(resp)
    assert isinstance(ret, (list, dict))
    return ret


async def hyprctl(command, base_command="dispatch") -> bool:
    """Run an IPC command. Returns success value."""
    if DEBUG:
        print(">>>", command)
    ctl_reader, ctl_writer = await asyncio.open_unix_connection(HYPRCTL)
    if isinstance(command, list):
        ctl_writer.write(
            f"[[BATCH]] {' ; '.join(f'{base_command} ' + c for c in command)}".encode()
        )
    else:
        ctl_writer.write(f"/{base_command} {command}".encode())
    await ctl_writer.drain()
    resp = await ctl_reader.read(100)
    ctl_writer.close()
    await ctl_writer.wait_closed()
    if DEBUG:
        print("<<<", resp)
    r: bool = resp == b"ok" * (len(resp) // 2)
    if DEBUG and not r:
        print(f"FAILED {resp}")
    return r


async def get_focused_monitor_props() -> dict[str, Any]:
    for monitor in await hyprctlJSON("monitors"):
        assert isinstance(monitor, dict)
        if monitor.get("focused") == True:
            return monitor
    raise RuntimeError("no focused monitor")
