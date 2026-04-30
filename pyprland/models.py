"""Type definitions and data models for Pyprland.

Provides TypedDict definitions matching Hyprland's JSON API responses:
- ClientInfo: Window/client properties
- MonitorInfo: Monitor/output properties
- WorkspaceDf: Workspace identifier

Also includes:
- Environment: Supported compositor/display server types
- ResponsePrefix: Protocol constants for daemon-client communication
- ExitCode: Standard CLI exit codes
- ReloadReason: Context for plugin on_reload() calls
- PyprError: Base exception for logged errors
"""

from dataclasses import dataclass
from enum import Enum, IntEnum, StrEnum, auto
from typing import Any, TypedDict

PlainTypes = float | str | dict[str, "PlainTypes"] | list["PlainTypes"]
JSONResponse = dict[str, PlainTypes] | list[dict[str, PlainTypes]] | PlainTypes


class RetensionTimes(float, Enum):
    """Cache retension times."""

    SHORT = 0.005
    LONG = 0.05


class WorkspaceDf(TypedDict):
    """Workspace definition."""

    id: int
    name: str


ClientInfo = TypedDict(
    "ClientInfo",
    {
        "address": str,
        "mapped": bool,
        "hidden": bool,
        "at": tuple[int, int],
        "size": tuple[int, int],
        "workspace": WorkspaceDf,
        "floating": bool,
        "monitor": int,
        "class": str,
        "title": str,
        "initialClass": str,
        "initialTitle": str,
        "pid": int,
        "xwayland": bool,
        "pinned": bool,
        "fullscreen": bool,
        "fullscreenMode": int,
        "fakeFullscreen": bool,
        "grouped": list[str],
        "swallowing": str,
        "focusHistoryID": int,
    },
)
"""Client information as returned by Hyprland."""


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

    to_disable: bool


@dataclass(order=True)
class VersionInfo:
    """Stores version information."""

    major: int = 0
    minor: int = 0
    micro: int = 0

    @classmethod
    def from_hyprctl(cls, data: dict[str, Any]) -> "VersionInfo":
        """Parse version from hyprctl JSON version output.

        Handles both stable releases (tag: "v0.40.0") and git builds
        (tag: "v0.40.0-127-g4e42107d"). For git builds, the micro
        version is incremented to represent "newer than release".

        Args:
            data: Parsed JSON from ``hyprctl -j version``

        Returns:
            Parsed VersionInfo instance.

        Raises:
            ValueError: If the version string cannot be parsed.
        """
        tag = data.get("tag")
        if tag and tag != "unknown":
            tag_stripped = str(tag).removeprefix("v")
            is_git_build = "-" in tag_stripped
            version_str = tag_stripped.split("-", 1)[0]
        else:
            is_git_build = False
            version_str = str(data.get("version", ""))

        parts = [int(i) for i in version_str.split(".")[:3]]
        if is_git_build:
            parts[-1] += 1
        return cls(*parts)


class PyprError(BaseException):
    """Used for errors which already triggered logging."""


# Exit codes for client
class ExitCode(IntEnum):
    """Standard exit codes for pypr client."""

    SUCCESS = 0
    USAGE_ERROR = 1  # No command provided, invalid arguments
    ENV_ERROR = 2  # Missing environment variables
    CONNECTION_ERROR = 3  # Cannot connect to daemon
    COMMAND_ERROR = 4  # Command execution failed


# Socket response protocol
class ResponsePrefix(StrEnum):
    """Response prefixes for daemon-client communication."""

    OK = "OK"
    ERROR = "ERROR"


class ReloadReason(Enum):
    """Reason for plugin reload/reconfiguration.

    Allows plugins to optimize behavior based on reload context:
    - INIT: First load during daemon startup (after init())
    - RELOAD: Configuration reload (pypr reload, pypr set, or plugin self-restart)
    """

    INIT = auto()
    RELOAD = auto()


class Environment(StrEnum):
    """Supported compositor/display server environments.

    Used for:
    - Plugin compatibility filtering (Plugin.environments)
    - Runtime environment detection (SharedState.environment)
    - Quickstart wizard environment selection
    """

    HYPRLAND = "hyprland"
    NIRI = "niri"
    WAYLAND = "wayland"  # Generic Wayland (no specific compositor)
    XORG = "xorg"  # X11/Xorg fallback
