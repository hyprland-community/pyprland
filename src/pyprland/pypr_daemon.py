"""Daemon startup functions for pyprland."""

import asyncio
import itertools
from pathlib import Path

from pyprland.constants import CONTROL
from pyprland.ipc import get_event_stream
from pyprland.manager import Pyprland
from pyprland.models import PyprError

__all__ = ["get_event_stream_with_retry", "run_daemon"]


async def get_event_stream_with_retry(
    max_retry: int = 10,
) -> tuple[asyncio.StreamReader, asyncio.StreamWriter] | tuple[None, BaseException]:
    """Obtain the event stream, retrying if it fails.

    If retry count is exhausted, returns (None, exception).

    Args:
        max_retry: Maximum number of retries
    """
    err_count = itertools.count()
    while True:
        attempt = next(err_count)
        try:
            return await get_event_stream()
        except (OSError, PyprError) as e:
            if attempt > max_retry:
                return None, e
            await asyncio.sleep(1)


async def run_daemon() -> None:
    """Run the server / daemon."""
    manager = Pyprland()

    # Ensure IPC folder exists (needed when no environment is running)
    ipc_folder = Path(CONTROL).parent
    try:
        ipc_folder.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        manager.log.critical("Cannot create IPC folder %s: %s", ipc_folder, e)
        return

    result = await get_event_stream_with_retry()
    if result[0] is None:
        events_reader, events_writer = None, None
        manager.log.warning("Failed to open hyprland event stream: %s.", result[1])
    else:
        events_reader, events_writer = result
        manager.event_reader = events_reader

    await manager.initialize()

    # Start server after initialization to avoid race conditions with plugin loading
    manager.server = await asyncio.start_unix_server(manager.read_command, CONTROL)

    manager.log.debug("[ initialized ]".center(80, "="))

    try:
        await manager.run()
    except KeyboardInterrupt:
        print("Interrupted")
    except asyncio.CancelledError:
        manager.log.critical("cancelled")
    else:
        await manager.exit_plugins()
        if events_writer:
            assert isinstance(events_writer, asyncio.StreamWriter)
            events_writer.close()
            await events_writer.wait_closed()
        manager.server.close()
        await manager.server.wait_closed()
