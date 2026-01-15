"""Niri adapter."""

import json
from typing import Any, cast

from ..common import notify_send
from ..ipc import niri_request
from ..models import ClientInfo, MonitorInfo
from .backend import EnvironmentBackend


class NiriBackend(EnvironmentBackend):
    """Niri backend implementation."""

    def parse_event(self, raw_data: str) -> tuple[str, Any] | None:
        """Parse a raw event string into (event_name, event_data)."""
        if not raw_data.strip().startswith("{"):
            return None
        try:
            event = json.loads(raw_data)
        except json.JSONDecodeError:
            self.log.exception("Invalid JSON event: %s", raw_data)
            return None

        if "Variant" in event:
            type_name = event["Variant"]["type"]
            data = event["Variant"]
            return f"niri_{type_name.lower()}", data
        return None

    async def execute(self, command: str | list[str], **kwargs: Any) -> bool:  # noqa: ANN401
        """Execute a command (or list of commands)."""
        weak = kwargs.get("weak", False)
        # Niri commands are typically lists of strings or objects, not a single string command line
        # If we receive a string, we might need to wrap it.
        # But looking at existing usage, nirictl expects list or dict.

        # If we receive a list of strings from execute(), it might be multiple commands?
        # Niri socket protocol is request-response JSON.

        try:
            ret = await niri_request(command, self.log)
            if isinstance(ret, dict) and "Ok" in ret:
                return True
        except Exception:  # pylint: disable=broad-exception-caught
            self.log.exception("Niri command failed")
            return False

        if weak:
            self.log.warning("Niri command failed: %s", ret)
        else:
            self.log.error("Niri command failed: %s", ret)
        return False

    async def execute_json(self, command: str, **kwargs: Any) -> Any:  # noqa: ANN401, ARG002
        """Execute a command and return the JSON result."""
        ret = await niri_request(command, self.log)
        if isinstance(ret, dict) and "Ok" in ret:
            return ret["Ok"]
        msg = f"Niri command failed: {ret}"
        raise RuntimeError(msg)

    async def get_clients(
        self,
        mapped: bool = True,
        workspace: str | None = None,
        workspace_bl: str | None = None,
    ) -> list[ClientInfo]:
        """Return the list of clients, optionally filtered."""
        return [
            self._map_niri_client(client)
            for client in cast("list[dict]", await self.execute_json("windows"))
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

    async def get_monitors(self) -> list[MonitorInfo]:
        """Return the list of monitors."""
        outputs = await self.execute_json("outputs")
        monitors = []
        for key, output in outputs.items():
            mon_info = cast(
                "MonitorInfo",
                {
                    "name": key,
                    "focused": output.get("is_focused", False),
                    "x": output.get("logical_position", {}).get("x", 0),
                    "y": output.get("logical_position", {}).get("y", 0),
                    "width": output.get("logical_size", {}).get("width", 0),
                    "height": output.get("logical_size", {}).get("height", 0),
                    "scale": output.get("scale", 1.0),
                    # Missing some fields that are specific to Hyprland or not exposed the same way in Niri
                    # Providing defaults to satisfy the TypedDict if possible
                    "id": -1,
                    "description": "",
                    "make": "",
                    "model": "",
                    "serial": "",
                    "refreshRate": 60.0,
                    "activeWorkspace": {"id": -1, "name": ""},
                    "specialWorkspace": {"id": -1, "name": ""},
                    "reserved": [],
                    "transform": 0,
                    "dpmsStatus": True,
                    "vrr": False,
                    "activelyTearing": False,
                    "disabled": False,
                    "currentFormat": "",
                    "availableModes": [],
                    "to_disable": False,
                },
            )
            monitors.append(mon_info)
        return monitors

    async def execute_batch(self, commands: list[str]) -> None:
        """Execute a batch of commands."""
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
            await self.execute(["action", cmd])

    async def notify(self, message: str, duration: int = 5000, color: str = "ff0000") -> None:
        """Send a notification."""
        # Niri doesn't have a built-in notification system exposed via IPC like Hyprland's `notify`
        # We rely on `notify-send` via the common utility

        await notify_send(message, duration, color)

    async def notify_info(self, message: str, duration: int = 5000) -> None:
        """Send an info notification."""
        await self.notify(message, duration, "0000ff")

    async def notify_error(self, message: str, duration: int = 5000) -> None:
        """Send an error notification."""
        await self.notify(message, duration, "ff0000")
