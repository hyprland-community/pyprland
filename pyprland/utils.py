"""Utilities."""

__all__ = ["get_mount_point", "get_max_length"]

import asyncio
import os
import time
from dataclasses import dataclass, field

from .types import JSONResponse


def get_mount_point(path: str) -> str:
    """Return the mount point of the given path."""
    path = os.path.abspath(path)
    while path != "/":
        if os.path.ismount(path):
            return path
        path = os.path.dirname(path)
    return path  # root '/' is the mount point for the topmost directory


def get_max_length(path: str) -> int:
    """Return the maximum length of a path in the given path's filesystem."""
    return os.pathconf(get_mount_point(path), "PC_PATH_MAX")


@dataclass
class CacheData:
    """Cache data structure."""

    retension_time: float
    expiration_date: float = 0
    payload: None | JSONResponse = field(default_factory=dict)
    _signal: asyncio.Event = field(default_factory=asyncio.Event)

    def set_pending(self, ref_time: float | None = None) -> None:
        """Set the current coroutine which will return the result.

        Will mark data as not ready yet, blocking awaiters of `wait_update`
        """
        self._signal.clear()
        self.expiration_date = (ref_time or time.time()) + self.retension_time
        self.payload = None

    def set_value(self, value: JSONResponse) -> None:
        """Set the cached value.

        Unblocks awaiters of `wait_update`
        """
        self.payload = value
        self._signal.set()

    async def wait_update(self) -> JSONResponse:
        """Wait for the cache data to be refreshed."""
        while True:
            if self.payload is not None:
                return self.payload
            await self._signal.wait()
