"""Common types from Hyprland API."""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import TypedDict

PlainTypes = float | str | dict[str, "PlainTypes"] | list["PlainTypes"]
JSONResponse = dict[str, PlainTypes] | list[dict[str, PlainTypes]]


class RetensionTimes(float, Enum):
    """Cache retension times."""

    SHORT: float = 0.005
    LONG: float = 0.05


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


class WorkspaceDf(TypedDict):
    """Workspace definition."""

    id: int
    name: str


class ClientInfo(TypedDict):
    """Client information as returned by Hyprland."""

    address: str
    mapped: bool
    hidden: bool
    at: tuple[int, int]
    size: tuple[int, int]
    workspace: WorkspaceDf
    floating: bool
    monitor: int
    class_: str
    title: str
    initialClass: str
    initialTitle: str
    pid: int
    xwayland: bool
    pinned: bool
    fullscreen: bool
    fullscreenMode: int
    fakeFullscreen: bool
    grouped: list[str]
    swallowing: str
    focusHistoryID: int


class MonitorInfo(TypedDict):
    """Monitor information as returned by Hyprland."""

    id: int
    name: str
    description: str
    make: str
    model: str
    serial: str
    width: int
    height: int
    refreshRate: float
    x: int
    y: int
    activeWorkspace: WorkspaceDf
    specialWorkspace: WorkspaceDf
    reserved: list[int]
    scale: float
    transform: int
    focused: bool
    dpmsStatus: bool
    vrr: bool
    activelyTearing: bool
    disabled: bool
    currentFormat: str
    availableModes: list[str]


@dataclass(order=True)
class VersionInfo:
    """Stores version information."""

    major: int = 0
    minor: int = 0
    micro: int = 0


class PyprError(BaseException):
    """Used for errors which already triggered logging."""
