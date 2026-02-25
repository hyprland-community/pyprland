"""Protocol definitions for plugin event handlers.

This module provides Protocol classes that document the expected signatures
for event handlers. Plugins don't need to inherit these - they exist for:

1. Documentation of expected event handler signatures
2. Optional mypy validation when plugins choose to inherit
3. Reference for test validation of handler signatures

Usage for plugin authors who want mypy validation::

    from pyprland.plugins.protocols import HyprlandEvents

    class Extension(HyprlandEvents, Plugin):
        async def event_monitoradded(self, name: str) -> None:
            ...  # mypy validates signature matches Protocol
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class HyprlandEvents(Protocol):
    """Protocol defining Hyprland event handler signatures.

    All event handlers receive a single string parameter.
    For events with no data (like configreloaded), an empty string is passed.

    See https://wiki.hyprland.org/IPC/ for the full list of Hyprland events.
    """

    async def event_activewindowv2(self, addr: str) -> None:
        """Window focus changed.

        Args:
            addr: Window address as hex string (without 0x prefix)
        """
        ...

    async def event_changefloatingmode(self, args: str) -> None:
        """Window floating mode changed.

        Args:
            args: Format "address,0|1" - address and floating state
        """
        ...

    async def event_closewindow(self, addr: str) -> None:
        """Window closed.

        Args:
            addr: Window address as hex string (without 0x prefix)
        """
        ...

    async def event_configreloaded(self, data: str = "") -> None:
        """Hyprland config reloaded.

        Args:
            data: Empty string (Hyprland sends no data for this event)
        """
        ...

    async def event_focusedmon(self, mon: str) -> None:
        """Monitor focus changed.

        Args:
            mon: Format "monitorname,workspacename"
        """
        ...

    async def event_monitoradded(self, name: str) -> None:
        """Monitor connected.

        Args:
            name: Monitor name (e.g., "DP-1", "HDMI-A-1")
        """
        ...

    async def event_monitorremoved(self, name: str) -> None:
        """Monitor disconnected.

        Args:
            name: Monitor name
        """
        ...

    async def event_openwindow(self, params: str) -> None:
        """Window opened.

        Args:
            params: Format "address,workspace,class,title"
        """
        ...

    async def event_workspace(self, workspace: str) -> None:
        """Workspace changed.

        Args:
            workspace: Workspace name (can be number or string)
        """
        ...


@runtime_checkable
class NiriEvents(Protocol):
    """Protocol defining Niri event handler signatures.

    Niri events pass JSON-parsed dict data.
    """

    async def niri_outputschanged(self, data: dict[str, Any]) -> None:
        """Outputs configuration changed.

        Args:
            data: Event data dictionary from Niri
        """
        ...
