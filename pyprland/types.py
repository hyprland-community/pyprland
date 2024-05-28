"""Common types from Hyprland API."""

import asyncio
from collections.abc import Coroutine
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypedDict


class RetensionTimes(float, Enum):
    """Cache retension times."""

    SHORT: float = 0.005
    LONG: float = 0.05


@dataclass
class CacheData:
    """Cache data structure."""

    retension_time: float
    expiration_date: float = 0
    payload: Coroutine | dict[str, Any] | list[dict[str, Any]] = field(default_factory=dict)
    signal: asyncio.Event = field(default_factory=asyncio.Event)


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
