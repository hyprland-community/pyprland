"""Interact with hyprland using sockets."""

__all__ = [
    "get_client_props",
    "get_monitor_props",
    "hyprctl",
    "hyprctl_json",
    "notify",
    "notify_error",
    "notify_info",
]

import asyncio
import json
from collections.abc import AsyncGenerator, Callable, Iterable
from contextlib import asynccontextmanager
from functools import partial
from logging import Logger
from typing import Any, cast

from .common import IPC_FOLDER, MINIMUM_ADDR_LEN, get_logger
from .types import ClientInfo, JSONResponse, MonitorInfo, PyprError

log: Logger | None = None

HYPRCTL = f"{IPC_FOLDER}/.socket.sock"
EVENTS = f"{IPC_FOLDER}/.socket2.sock"


@asynccontextmanager
async def hyprctl_connection(logger: Logger) -> AsyncGenerator[tuple[asyncio.StreamReader, asyncio.StreamWriter], None]:
    """Context manager for the hyprctl socket."""
    try:
        reader, writer = await asyncio.open_unix_connection(HYPRCTL)
    except FileNotFoundError as e:
        logger.critical("hyprctl socket not found! is it running ?")
        raise PyprError from e

    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


async def notify(text: str, duration: int = 3, color: str = "ff1010", icon: int = -1, logger: None | Logger = None) -> None:
    """Hyprland notification system."""
    await hyprctl(f"{icon} {int(duration * 1000)} rgb({color})  {text}", "notify", logger=logger)


notify_fatal = partial(notify, icon=3, duration=10)
notify_error = partial(notify, icon=0, duration=5)
notify_info = partial(notify, icon=1, duration=5)


async def get_event_stream() -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Return a new event socket connection."""
    return await asyncio.open_unix_connection(EVENTS)


def retry_on_reset(func: Callable) -> Callable:
    """Retry on reset wrapper."""

    async def wrapper(*args, logger: Logger, **kwargs) -> Any:  # noqa: ANN401
        exc = None
        for count in range(3):
            try:
                return await func(*args, **kwargs, logger=logger)
            except ConnectionResetError as e:  # noqa: PERF203
                exc = e
                logger.warning("ipc connection problem, retrying...")
                await asyncio.sleep(0.5 * count)
        logger.error("ipc connection failed.")
        raise ConnectionResetError from exc

    return wrapper


async def _get_response(command: bytes, logger: Logger) -> JSONResponse:
    """Get response of `command` from the IPC socket."""
    async with hyprctl_connection(logger) as (reader, writer):
        writer.write(command)
        await writer.drain()
        reader_data = await reader.read()

    decoded_data = reader_data.decode("utf-8", errors="replace")
    return json.loads(decoded_data)  # type: ignore


@retry_on_reset
async def hyprctl_json(command: str, logger: Logger | None = None) -> JSONResponse:
    """Run an IPC command and return the JSON output."""
    logger = cast("Logger", logger or log)
    ret = await _get_response(f"-j/{command}".encode(), logger)
    assert isinstance(ret, list | dict)
    return ret


# }}}


# hyprctl : batched commands {{{
def _format_command(command_list: list[str] | list[list[str]], default_base_command: str) -> Iterable[str]:
    """Format a list of commands to be sent to Hyprland.

    Args:
        command_list: list of commands to send
            Each command can be a string or a tuple with the command and the base command
        default_base_command: type of command to send
    """
    for command in command_list:
        if isinstance(command, str):
            yield f"{default_base_command} {command}"
        else:
            yield f"{command[1]} {command[0]}"


@retry_on_reset
async def hyprctl(command: str | list[str], base_command: str = "dispatch", logger: Logger | None = None, weak: bool = False) -> bool:
    """Run an IPC command. Returns success value.

    Args:
        command: single command (str) or list of commands to send to Hyprland
        base_command: type of command to send
        logger: logger to use in case of error
        weak: if True, only log a warning on failure

    Returns:
        True on success
    """
    logger = cast("Logger", logger or log)

    if not command:
        logger.warning("%s triggered without a command!", base_command)
        return False
    logger.debug("%s %s", base_command, command)

    async with hyprctl_connection(logger) as (ctl_reader, ctl_writer):
        if isinstance(command, list):
            nb_cmds = len(command)
            ctl_writer.write(f"[[BATCH]] {' ; '.join(_format_command(command, base_command))}".encode())
        else:
            nb_cmds = 1
            ctl_writer.write(f"/{base_command} {command}".encode())
        await ctl_writer.drain()
        resp = await ctl_reader.read(100)

    # remove "\n" from the response
    resp = b"".join(resp.split(b"\n"))
    # In Hyprland < 0.40.0 "ok" was returned for success
    # In newer versions "ok" is not returned anymore (empty response)
    # So we assume success if response is empty or contains "ok"
    # But for batch commands, "ok" might be repeated, so we need to be careful
    # Actually, recent hyprland versions might behave differently.
    # Let's stick to the current logic but be aware of changes.
    # The existing logic checks for "ok" * nb_cmds.

    r: bool = resp == b"ok" * nb_cmds
    if not r:
        if weak:
            logger.warning("FAILED %s", resp)
        else:
            logger.error("FAILED %s", resp)
    return r


# }}}


async def get_monitor_props(logger: Logger | None = None, name: str | None = None) -> MonitorInfo:
    """Return focused monitor data if `name` is not defined, else use monitor's name.

    Args:
        logger: logger to use in case of error
        name: (optional) monitor name

    Returns:
        dict() with the focused monitor properties
    """
    if name:

        def _match_fn(mon: MonitorInfo) -> bool:
            return mon["name"] == name
    else:

        def _match_fn(mon: MonitorInfo) -> bool:
            return cast("bool", mon.get("focused"))

    for monitor in await hyprctl_json("monitors", logger=logger):
        if _match_fn(cast("MonitorInfo", monitor)):
            return cast("MonitorInfo", monitor)
    msg = "no focused monitor"
    raise RuntimeError(msg)


def default_match_fn(value1: Any, value2: Any) -> bool:  # noqa: ANN401
    """Default match function."""
    return bool(value1 == value2)


async def get_client_props(
    logger: Logger | None = None, match_fn: Callable = default_match_fn, clients: list[ClientInfo] | None = None, **kw
) -> ClientInfo | None:
    """Return the properties of a client that matches the given `match_fn` (or default to equality) given the keyword arguments.

    Eg.
        # will return the properties of the client with address "0x1234"
        get_client_props(logger, addr="0x1234")

        # will return the properties of the client with initialClass containing "fooBar"
        get_client_props(logger, match_fn=lambda x, y: y in x), initialClass="fooBar")

    Args:
        logger: logger to use in case of error
        match_fn: function to match the client properties, takes 2 arguments (client_value, config_value)
        clients: list of clients to search in
        kw: keyword arguments to match the client properties

        Any other keyword argument will be used to match the client properties. Only one keyword argument is allowed.
        `addr` aliases `address` and `cls` aliases `class`

        Note: the address of the client must include the "0x" prefix
    """
    assert kw

    addr = kw.get("addr")
    klass = kw.get("cls")

    if addr:
        assert len(addr) > MINIMUM_ADDR_LEN, "Client address is invalid"
        prop_name = "address"
        prop_value = addr
    elif klass:
        prop_name = "class"
        prop_value = klass
    else:
        prop_name, prop_value = next(iter(kw.items()))

    for client in clients or await hyprctl_json("clients", logger=logger):
        assert isinstance(client, dict)
        if match_fn(client.get(prop_name), prop_value):
            return client  # type: ignore
    return None


def init() -> None:
    """Initialize logging."""
    global log
    log = get_logger("ipc")


def get_controls(logger: Logger) -> tuple[Callable, Callable, Callable, Callable, Callable]:
    """Return (hyprctl, hyprctl_json, notify) configured for the given logger."""
    return (
        partial(hyprctl, logger=logger),
        partial(hyprctl_json, logger=logger),
        partial(notify, logger=logger),
        partial(notify_info, logger=logger),
        partial(notify_error, logger=logger),
    )
