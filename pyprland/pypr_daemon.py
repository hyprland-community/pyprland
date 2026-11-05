"""Daemon startup functions for pyprland."""

import asyncio
import itertools
import os
from logging import Logger
from pathlib import Path

from pyprland.aioops import aiexists, aiunlink
from pyprland.constants import CONTROL, LOCK
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


def _acquire_lock(log: Logger) -> bool:
    """Acquire the daemon lock file. Returns True if acquired.

    If a lock exists and the owning process is still alive, logs an error
    and returns False. Stale locks (dead PID) are removed.
    """
    lock_path = Path(LOCK)
    if lock_path.exists():
        try:
            pid = int(lock_path.read_text().strip())
            os.kill(pid, 0)  # raises ProcessLookupError if not alive
        except (ValueError, ProcessLookupError, PermissionError, OSError):
            pass  # stale or unreadable lock — remove it
        else:
            log.critical("pyprland is already running (pid %d).", pid)
            return False
        lock_path.unlink(missing_ok=True)
    lock_path.write_text(str(os.getpid()))
    return True


def _release_lock() -> None:
    """Remove the daemon lock file."""
    Path(LOCK).unlink(missing_ok=True)


async def run_daemon() -> None:  # noqa: C901, PLR0912, PLR0915
    """Run the server / daemon."""
    manager = Pyprland()
    server_started = False

    # Ensure IPC folder exists (needed when no environment is running)
    ipc_folder = Path(CONTROL).parent
    try:
        ipc_folder.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        manager.log.critical("Cannot create IPC folder %s: %s", ipc_folder, e)
        return

    # Acquire lock to prevent a second daemon from starting
    if not _acquire_lock(manager.log):
        return

    try:
        result = await get_event_stream_with_retry()
        if result[0] is None:
            events_reader, events_writer = None, None
            manager.log.warning("Failed to open hyprland event stream: %s.", result[1])
        else:
            events_reader, events_writer = result
            manager.event_reader = events_reader

        await manager.initialize()

        # Start server after initialization to avoid race conditions with plugin loading
        try:
            manager.server = await asyncio.start_unix_server(manager.read_command, CONTROL)
            server_started = True
        except OSError as e:
            manager.log.critical(
                "Failed to bind %s: %s (another pyprland instance may be running).",
                CONTROL,
                e,
            )
            await manager.exit_plugins()
            if events_writer:
                assert isinstance(events_writer, asyncio.StreamWriter)
                events_writer.close()
                await events_writer.wait_closed()
            return

        manager.log.debug("[ initialized ]".center(80, "="))

        try:
            await manager.run()
        except KeyboardInterrupt:
            print("Interrupted")
        except asyncio.CancelledError:
            manager.log.critical("cancelled")
        finally:
            await manager.exit_plugins()
            if events_writer:
                assert isinstance(events_writer, asyncio.StreamWriter)
                events_writer.close()
                await events_writer.wait_closed()
            if server_started:
                manager.server.close()
                await manager.server.wait_closed()
                if await aiexists(CONTROL):
                    await aiunlink(CONTROL)
    finally:
        _release_lock()
