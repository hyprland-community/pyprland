"""Niri adapter."""

import json
from logging import Logger
from typing import Any, cast

from ..common import notify_send
from ..constants import DEFAULT_NOTIFICATION_DURATION_MS, DEFAULT_REFRESH_RATE_HZ
from ..ipc import niri_request
from ..models import ClientInfo, MonitorInfo
from .backend import EnvironmentBackend

# Niri transform string to Hyprland-compatible integer mapping
# Keys are lowercase for case-insensitive lookup
NIRI_TRANSFORM_MAP: dict[str, int] = {
    "normal": 0,
    "90": 1,
    "180": 2,
    "270": 3,
    "flipped": 4,
    "flipped90": 5,
    "flipped-90": 5,
    "flipped180": 6,
    "flipped-180": 6,
    "flipped270": 7,
    "flipped-270": 7,
}


def get_niri_transform(value: str, default: int = 0) -> int:
    """Get transform integer from Niri transform string (case-insensitive).

    Args:
        value: Transform string like "Normal", "90", "Flipped-90", etc.
        default: Value to return if not found

    Returns:
        Integer transform value (0-7)
    """
    return NIRI_TRANSFORM_MAP.get(value.lower(), default)


def niri_output_to_monitor_info(name: str, data: dict[str, Any]) -> MonitorInfo:
    """Convert Niri output data to MonitorInfo.

    Handles both Niri output formats:
    - Format A: Uses "logical" object with nested x, y, scale, transform
    - Format B: Uses "logical_position", "logical_size", "scale" at root level

    Args:
        name: Output name (e.g., "DP-1")
        data: Niri output data dictionary

    Returns:
        MonitorInfo TypedDict with normalized fields
    """
    # Try format A first (more detailed - has modes, logical object)
    logical = data.get("logical") or {}
    mode: dict[str, Any] = next((m for m in data.get("modes", []) if m.get("is_active")), {})

    # Fall back to format B for position/size if format A fields missing
    x = logical.get("x") if logical else data.get("logical_position", {}).get("x", 0)
    y = logical.get("y") if logical else data.get("logical_position", {}).get("y", 0)
    scale = logical.get("scale") if logical else data.get("scale", 1.0)

    # Width/height: prefer active mode, fall back to logical_size
    width = mode.get("width") if mode else data.get("logical_size", {}).get("width", 0)
    height = mode.get("height") if mode else data.get("logical_size", {}).get("height", 0)

    # Refresh rate from mode (in mHz), default to 60Hz
    refresh_rate = mode.get("refresh_rate", DEFAULT_REFRESH_RATE_HZ * 1000) / 1000.0 if mode else DEFAULT_REFRESH_RATE_HZ

    # Transform from logical object
    transform_str = logical.get("transform", "Normal") if logical else "Normal"

    # Build description from make/model if available
    make = data.get("make", "")
    model = data.get("model", "")
    description = f"{make} {model}".strip() if make or model else ""

    return cast(
        "MonitorInfo",
        {
            "name": name,
            "description": description,
            "make": make,
            "model": model,
            "serial": data.get("serial", ""),
            "width": width,
            "height": height,
            "refreshRate": refresh_rate,
            "x": x if x is not None else 0,
            "y": y if y is not None else 0,
            "scale": scale if scale is not None else 1.0,
            "transform": get_niri_transform(transform_str),
            "focused": data.get("is_focused", False),
            # Fields not available in Niri - provide sensible defaults
            "id": -1,
            "activeWorkspace": {"id": -1, "name": ""},
            "specialWorkspace": {"id": -1, "name": ""},
            "reserved": [],
            "dpmsStatus": True,
            "vrr": False,
            "activelyTearing": False,
            "disabled": False,
            "currentFormat": "",
            "availableModes": [],
            "to_disable": False,
        },
    )


class NiriBackend(EnvironmentBackend):
    """Niri backend implementation."""

    def parse_event(self, raw_data: str, *, log: Logger) -> tuple[str, Any] | None:
        """Parse a raw event string into (event_name, event_data).

        Args:
            raw_data: Raw event string from the compositor
            log: Logger to use for this operation
        """
        if not raw_data.strip().startswith("{"):
            return None
        try:
            event = json.loads(raw_data)
        except json.JSONDecodeError:
            log.exception("Invalid JSON event: %s", raw_data)
            return None

        if "Variant" in event:
            type_name = event["Variant"]["type"]
            data = event["Variant"]
            return f"niri_{type_name.lower()}", data
        return None

    async def execute(self, command: str | list | dict, *, log: Logger, **kwargs: Any) -> bool:  # noqa: ANN401
        """Execute a command (or list of commands).

        Args:
            command: The command to execute
            log: Logger to use for this operation
            **kwargs: Additional arguments (weak, etc.)
        """
        weak = kwargs.get("weak", False)
        # Niri commands are typically lists of strings or objects, not a single string command line
        # If we receive a string, we might need to wrap it.
        # But looking at existing usage, nirictl expects list or dict.

        # If we receive a list of strings from execute(), it might be multiple commands?
        # Niri socket protocol is request-response JSON.

        try:
            ret = await niri_request(command, log)
            if isinstance(ret, dict) and "Ok" in ret:
                return True
        except (OSError, ConnectionError, json.JSONDecodeError) as e:
            log.warning("Niri command failed: %s", e)
            return False

        if weak:
            log.warning("Niri command failed: %s", ret)
        else:
            log.error("Niri command failed: %s", ret)
        return False

    async def execute_json(self, command: str, *, log: Logger, **kwargs: Any) -> Any:  # noqa: ANN401, ARG002
        """Execute a command and return the JSON result.

        Args:
            command: The command to execute
            log: Logger to use for this operation
            **kwargs: Additional arguments
        """
        ret = await niri_request(command, log)
        if isinstance(ret, dict) and "Ok" in ret:
            return ret["Ok"]
        msg = f"Niri command failed: {ret}"
        raise RuntimeError(msg)

    async def get_clients(
        self,
        mapped: bool = True,
        workspace: str | None = None,
        workspace_bl: str | None = None,
        *,
        log: Logger,
    ) -> list[ClientInfo]:
        """Return the list of clients, optionally filtered.

        Args:
            mapped: If True, only return mapped clients
            workspace: Filter to this workspace name
            workspace_bl: Blacklist this workspace name
            log: Logger to use for this operation
        """
        return [
            self._map_niri_client(client)
            for client in cast("list[dict]", await self.execute_json("windows", log=log))
            if (not mapped or client.get("is_mapped", True))
            and (workspace is None or str(client.get("workspace_id")) == workspace)
            and (workspace_bl is None or str(client.get("workspace_id")) != workspace_bl)
        ]

    def _map_niri_client(self, niri_client: dict[str, Any]) -> ClientInfo:
        """Helper to map Niri window dict to ClientInfo TypedDict."""
        return cast(
            "ClientInfo",
            {
                "address": str(niri_client.get("id")),
                "class": niri_client.get("app_id"),
                "title": niri_client.get("title"),
                "workspace": {"name": str(niri_client.get("workspace_id"))},
                "pid": -1,
                "mapped": niri_client.get("is_mapped", True),
                "hidden": False,
                "at": (0, 0),
                "size": (0, 0),
                "floating": False,
                "monitor": -1,
                "initialClass": niri_client.get("app_id"),
                "initialTitle": niri_client.get("title"),
                "xwayland": False,
                "pinned": False,
                "fullscreen": False,
                "fullscreenMode": 0,
                "fakeFullscreen": False,
                "grouped": [],
                "swallowing": "",
                "focusHistoryID": 0,
            },
        )

    async def get_monitors(self, *, log: Logger, include_disabled: bool = False) -> list[MonitorInfo]:  # noqa: ARG002
        """Return the list of monitors.

        Args:
            log: Logger to use for this operation
            include_disabled: Ignored for Niri (no concept of disabled monitors)
        """
        outputs = await self.execute_json("outputs", log=log)
        return [niri_output_to_monitor_info(name, output) for name, output in outputs.items()]

    async def execute_batch(self, commands: list[str], *, log: Logger) -> None:
        """Execute a batch of commands.

        Args:
            commands: List of commands to execute
            log: Logger to use for this operation
        """
        # Niri doesn't support batching in the same way, so we iterate
        for cmd in commands:
            # We need to parse the command string into an action
            # This is a bit tricky as niri commands are structured objects/lists
            # For now, let's assume 'action' is a command to be sent via nirictl
            # But wait, execute_batch typically receives "dispatch <cmd>" type strings for Hyprland.
            # We need to adapt this.

            # Simple adaptation: if it's a known string command, we try to map it or just send it if niri accepts string commands
            # (it mostly uses 'action' msg)
            # This part requires more knowledge of how commands are passed.
            # In current Pyprland, nirictl takes a list or dict.

            # Placeholder implementation:
            await self.execute(["action", cmd], log=log)

    async def notify(
        self,
        message: str,
        duration: int = DEFAULT_NOTIFICATION_DURATION_MS,
        color: str = "ff0000",  # noqa: ARG002
        *,
        log: Logger,  # noqa: ARG002
    ) -> None:
        """Send a notification.

        Args:
            message: The notification message
            duration: Duration in milliseconds
            color: Hex color code
            log: Logger to use for this operation (unused - notify_send doesn't log)
        """
        # Niri doesn't have a built-in notification system exposed via IPC like Hyprland's `notify`
        # We rely on `notify-send` via the common utility

        await notify_send(message, duration, color)

    # ─── Window Operation Helpers (Niri overrides) ────────────────────────────

    async def focus_window(self, address: str, *, log: Logger) -> bool:
        """Focus a window by ID.

        Args:
            address: Window ID
            log: Logger to use for this operation
        """
        return await self.execute({"Action": {"FocusWindow": {"id": int(address)}}}, log=log)

    async def move_window_to_workspace(
        self,
        address: str,
        workspace: str,
        *,
        silent: bool = True,  # noqa: ARG002
        log: Logger,
    ) -> bool:
        """Move a window to a workspace (silent parameter ignored in Niri).

        Args:
            address: Window ID
            workspace: Target workspace ID
            silent: Ignored in Niri
            log: Logger to use for this operation
        """
        return await self.execute(
            {"Action": {"MoveWindowToWorkspace": {"window_id": int(address), "reference": {"Id": int(workspace)}}}},
            log=log,
        )

    async def pin_window(self, address: str, *, log: Logger) -> bool:  # noqa: ARG002
        """Toggle pin state - not available in Niri.

        Args:
            address: Window ID (unused)
            log: Logger to use for this operation
        """
        log.debug("pin_window: not available in Niri")
        return False

    async def close_window(self, address: str, *, log: Logger) -> bool:
        """Close a window by ID.

        Args:
            address: Window ID
            log: Logger to use for this operation
        """
        return await self.execute({"Action": {"CloseWindow": {"id": int(address)}}}, log=log)

    async def resize_window(self, address: str, width: int, height: int, *, log: Logger) -> bool:  # noqa: ARG002
        """Resize a window - not available in Niri (tiling WM).

        Args:
            address: Window ID (unused)
            width: Target width (unused)
            height: Target height (unused)
            log: Logger to use for this operation
        """
        log.debug("resize_window: not available in Niri")
        return False

    async def move_window(self, address: str, x: int, y: int, *, log: Logger) -> bool:  # noqa: ARG002
        """Move a window to exact position - not available in Niri (tiling WM).

        Args:
            address: Window ID (unused)
            x: Target x position (unused)
            y: Target y position (unused)
            log: Logger to use for this operation
        """
        log.debug("move_window: not available in Niri")
        return False

    async def toggle_floating(self, address: str, *, log: Logger) -> bool:  # noqa: ARG002
        """Toggle floating state - not available in Niri.

        Args:
            address: Window ID (unused)
            log: Logger to use for this operation
        """
        log.debug("toggle_floating: not available in Niri")
        return False

    async def set_keyword(self, keyword_command: str, *, log: Logger) -> bool:  # noqa: ARG002
        """Execute a keyword command - not available in Niri.

        Args:
            keyword_command: The keyword command (unused)
            log: Logger to use for this operation
        """
        log.debug("set_keyword: not available in Niri")
        return False
