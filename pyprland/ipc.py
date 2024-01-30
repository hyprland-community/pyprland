#!/bin/env python
""" Interact with hyprland using sockets """
import asyncio
import json
import os
from typing import Any
from logging import Logger
from functools import partial

from .common import PyprError, get_logger

log: Logger | None = None

HYPRCTL = f'/tmp/hypr/{ os.environ["HYPRLAND_INSTANCE_SIGNATURE"] }/.socket.sock'
EVENTS = f'/tmp/hypr/{ os.environ["HYPRLAND_INSTANCE_SIGNATURE"] }/.socket2.sock'


async def notify(text, duration=3, color="ff1010", icon=-1, logger=None):
    "Uses hyprland notification system"
    await hyprctl(
        f"{icon} {int(duration*1000)} rgb({color})  {text}", "notify", logger=logger
    )


notify_fatal = partial(notify, icon=3, duration=10)
notify_error = partial(notify, icon=0, duration=5)
notify_info = partial(notify, icon=1, duration=5)


async def get_event_stream():
    "Returns a new event socket connection"
    return await asyncio.open_unix_connection(EVENTS)


async def hyprctlJSON(command, logger=None) -> list[dict[str, Any]] | dict[str, Any]:
    """Run an IPC command and return the JSON output."""
    logger = logger or log
    logger.debug(command)
    try:
        ctl_reader, ctl_writer = await asyncio.open_unix_connection(HYPRCTL)
    except FileNotFoundError as e:
        logger.critical("hyprctl socket not found! is it running ?")
        raise PyprError() from e
    ctl_writer.write(f"-j/{command}".encode())
    await ctl_writer.drain()
    resp = await ctl_reader.read()
    ctl_writer.close()
    await ctl_writer.wait_closed()
    ret = json.loads(resp)
    assert isinstance(ret, (list, dict))
    return ret


def _format_command(command_list, default_base_command):
    "helper function to format BATCH commands"
    for command in command_list:
        if isinstance(command, str):
            yield f"{default_base_command} {command}"
        else:
            yield f"{command[1]} {command[0]}"


async def hyprctl(command, base_command="dispatch", logger=None) -> bool:
    """Run an IPC command. Returns success value."""
    logger = logger or log
    logger.debug("%s %s", base_command, command)
    try:
        ctl_reader, ctl_writer = await asyncio.open_unix_connection(HYPRCTL)
    except FileNotFoundError as e:
        logger.critical("hyprctl socket not found! is it running ?")
        raise PyprError() from e

    if isinstance(command, list):
        nb_cmds = len(command)
        ctl_writer.write(
            f"[[BATCH]] {' ; '.join(_format_command(command, base_command))}".encode()
        )
    else:
        nb_cmds = 1
        ctl_writer.write(f"/{base_command} {command}".encode())
    await ctl_writer.drain()
    resp = await ctl_reader.read(100)
    ctl_writer.close()
    await ctl_writer.wait_closed()
    r: bool = resp == b"ok" * nb_cmds
    if not r:
        logger.error("FAILED %s", resp)
    return r


async def get_focused_monitor_props(logger=None) -> dict[str, Any]:
    "Returns focused monitor data"
    for monitor in await hyprctlJSON("monitors", logger=logger):
        assert isinstance(monitor, dict)
        if monitor.get("focused"):
            return monitor
    raise RuntimeError("no focused monitor")


async def get_client_props(
    addr: str | None = None, pid: int | None = None, cls: str | None = None, logger=None
):
    "Returns client properties given its address"
    assert addr or pid or cls

    if addr:
        assert len(addr) > 2, "Client address is invalid"
        prop_name = "address"
        prop_value = addr
    elif cls:
        prop_name = "class"
        prop_value = cls
    else:
        assert pid, "Client pid is invalid"
        prop_name = "pid"
        prop_value = pid

    for client in await hyprctlJSON("clients", logger=logger):
        assert isinstance(client, dict)
        if client.get(prop_name) == prop_value:
            return client


def init():
    "initialize logging"
    global log
    log = get_logger("ipc")


def getCtrlObjects(logger):
    "Returns (hyprctl, hyprctlJSON, notify) configured for the given logger"
    return (
        partial(hyprctl, logger=logger),
        partial(hyprctlJSON, logger=logger),
        partial(notify, logger=logger),
    )
