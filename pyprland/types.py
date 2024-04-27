" Common types from Hyprland API"

from dataclasses import dataclass
from typing import TypedDict


class WorkspaceDf(TypedDict):
    "Workspace definition"
    id: int
    name: str


class ClientInfo(TypedDict):
    "Client information as returned by Hyprland"
    address: str
    mapped: bool
    hidden: bool
    at: list[int]
    size: list[int]
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
    "Monitor information as returned by Hyprland"
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
    "Stores version information"
    major: int = 0  # noqa: F841
    minor: int = 0  # noqa: F841
    micro: int = 0  # noqa: F841


class PyprError(Exception):
    """Used for errors which already triggered logging"""
