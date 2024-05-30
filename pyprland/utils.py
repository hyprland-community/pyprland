"""Utilities."""

__all__ = ["CacheData"]

import asyncio
import time
from dataclasses import dataclass, field

from .types import JSONResponse


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
