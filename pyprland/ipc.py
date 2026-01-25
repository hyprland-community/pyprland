"""Interact with hyprland using sockets."""

__all__ = [
    "get_response",
    "hyprctl_connection",
    "niri_connection",
    "niri_request",
    "retry_on_reset",
]

import asyncio
import json
import os
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from logging import Logger
from typing import Any

from .common import IPC_FOLDER, get_logger
from .constants import IPC_MAX_RETRIES, IPC_RETRY_DELAY_MULTIPLIER
from .models import JSONResponse, PyprError


class _IpcState:
    """Module-level state container to avoid global statements."""

    log: Logger | None = None
    notify_method: str = "auto"


_state = _IpcState()

HYPRCTL = f"{IPC_FOLDER}/.socket.sock"
EVENTS = f"{IPC_FOLDER}/.socket2.sock"
NIRI_SOCKET = os.environ.get("NIRI_SOCKET")


@asynccontextmanager
async def hyprctl_connection(logger: Logger) -> AsyncGenerator[tuple[asyncio.StreamReader, asyncio.StreamWriter], None]:
    """Context manager for the hyprctl socket.

    Args:
        logger: Logger to use for error reporting
    """
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


@asynccontextmanager
async def niri_connection(logger: Logger) -> AsyncGenerator[tuple[asyncio.StreamReader, asyncio.StreamWriter], None]:
    """Context manager for the niri socket.

    Args:
        logger: Logger to use for error reporting
    """
    if not NIRI_SOCKET:
        logger.critical("NIRI_SOCKET not set!")
        msg = "Niri is not available"
        raise PyprError(msg)
    try:
        reader, writer = await asyncio.open_unix_connection(NIRI_SOCKET)
    except FileNotFoundError as e:
        logger.critical("niri socket not found! is it running ?")
        raise PyprError from e

    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


def set_notify_method(method: str) -> None:
    """Set the notification method.

    Args:
        method: The method to use ("auto", "native", "notify-send")
    """
    _state.notify_method = method


async def get_event_stream() -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
    """Return a new event socket connection."""
    if NIRI_SOCKET:
        async with niri_connection(_state.log or get_logger()) as (reader, writer):
            writer.write(b'"EventStream"')
            await writer.drain()
            # We must return the reader/writer, so we detach them from the context manager?
            # actually niri_connection closes on exit.
            # We can't use the context manager here easily if we want to return the stream.
            # Let's just duplicate the connection logic for this specific case or adapt niri_connection

    if NIRI_SOCKET:
        reader, writer = await asyncio.open_unix_connection(NIRI_SOCKET)
        writer.write(b'"EventStream"')
        await writer.drain()
        return reader, writer

    return await asyncio.open_unix_connection(EVENTS)


def retry_on_reset(func: Callable) -> Callable:
    """Retry on reset wrapper.

    Args:
        func: The function to wrap
    """

    async def wrapper(*args, log: Logger | None = None, logger: Logger | None = None, **kwargs) -> Any:  # noqa: ANN401
        # Support both 'log' and 'logger' parameter names
        effective_log = log or logger
        if effective_log is None and args and hasattr(args[0], "log"):
            effective_log = args[0].log
        assert effective_log is not None
        exc = None
        for count in range(IPC_MAX_RETRIES):
            try:
                # Pass as 'log' for backend methods, 'logger' for IPC functions
                if "log" in func.__code__.co_varnames:
                    return await func(*args, **kwargs, log=effective_log)
                return await func(*args, **kwargs, logger=effective_log)
            except ConnectionResetError as e:  # noqa: PERF203
                exc = e
                effective_log.warning("ipc connection problem, retrying...")
                await asyncio.sleep(IPC_RETRY_DELAY_MULTIPLIER * count)
        effective_log.error("ipc connection failed.")
        raise ConnectionResetError from exc

    return wrapper


@retry_on_reset
async def niri_request(payload: str | dict | list, logger: Logger) -> JSONResponse:
    """Send request to Niri and return response."""
    async with niri_connection(logger) as (reader, writer):
        writer.write(json.dumps(payload).encode())
        await writer.drain()
        response = await reader.readline()
        if not response:
            msg = "Empty response from Niri"
            raise PyprError(msg)
        return json.loads(response)  # type: ignore


async def get_response(command: bytes, logger: Logger) -> JSONResponse:
    """Get response of `command` from the IPC socket.

    Args:
        command: The command to send as bytes
        logger: Logger to use for the connection
    """
    async with hyprctl_connection(logger) as (reader, writer):
        writer.write(command)
        await writer.drain()
        reader_data = await reader.read()

    decoded_data = reader_data.decode("utf-8", errors="replace")
    return json.loads(decoded_data)  # type: ignore


def init() -> None:
    """Initialize logging."""
    _state.log = get_logger("ipc")
