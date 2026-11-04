"""Niri compositor backend implementation.

Backend for Niri compositor using its JSON-based IPC protocol.
Maps Niri's window/output data structures to Hyprland-compatible formats.
Some operations (pin, resize, move) are unavailable due to Niri's tiling nature.
"""

import json
import re
from collections.abc import Iterable
from logging import Logger
from typing import Any, cast

from ..common import SharedState
from ..constants import DEFAULT_REFRESH_RATE_HZ
from ..ipc import niri_request
from ..models import ClientInfo, JSONResponse, MonitorInfo
from .backend import EnvironmentBackend
from .notifier import Notifier, NotifySendNotifier

# Niri transform string to Hyprland-compatible integer mapping (lowercase keys)
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


def niri_output_to_monitor_info(name: str, data: dict[str, Any], index: int = -1) -> MonitorInfo:
    """Convert Niri output data to MonitorInfo.

    Args:
        name: Output name (e.g., "DP-1")
        data: Niri output data dictionary
        index: Synthetic monitor id. Niri has no numeric output ids, so callers
            pass a stable index (see `monitor_ids`) to emulate Hyprland's.

    Returns:
        MonitorInfo TypedDict with normalized fields
    """
    logical = data.get("logical") or {}

    # Niri marks the active mode with the `current_mode` index rather than a
    # flag on the mode itself.
    modes = data.get("modes") or []
    current = data.get("current_mode")
    mode: dict[str, Any] = modes[current] if isinstance(current, int) and 0 <= current < len(modes) else {}

    scale = logical.get("scale") or data.get("scale") or 1.0

    # Width/height are the physical resolution, as Hyprland reports them;
    # `get_size()` applies the scale. Fall back to the logical size scaled back
    # up when no mode is available.
    if mode:
        width, height = mode.get("width", 0), mode.get("height", 0)
    else:
        width = int((logical.get("width") or 0) * scale)
        height = int((logical.get("height") or 0) * scale)

    x = logical.get("x", 0)
    y = logical.get("y", 0)

    # Refresh rate is reported in mHz.
    refresh_rate = mode.get("refresh_rate", DEFAULT_REFRESH_RATE_HZ * 1000) / 1000.0 if mode else DEFAULT_REFRESH_RATE_HZ

    transform_str = logical.get("transform", "Normal")

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
            "focused": False,  # Niri outputs carry no focus flag; see _attach_active_workspaces
            # Fields not available in Niri - provide sensible defaults
            "id": index,
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


def monitor_ids(output_names: Iterable[str]) -> dict[str, int]:
    """Assign a stable numeric id to each Niri output.

    Niri identifies outputs by name only, while the Hyprland-shaped models used
    across Pyprland expect numeric monitor ids. Sorting by name keeps the ids
    stable between calls as long as the set of connected outputs doesn't change.

    Args:
        output_names: The connected output names

    Returns:
        Mapping of output name to its synthetic id
    """
    return {name: i for i, name in enumerate(sorted(output_names))}


def niri_workspace_reference(workspace: str) -> dict[str, Any]:
    """Build the Niri reference for a workspace given as an id or a name.

    Pyprland identifies Niri workspaces by their numeric id, but scratchpads
    park on workspaces the user declared by name, so both forms occur.

    Args:
        workspace: A workspace id or name

    Returns:
        The reference object Niri expects
    """
    return {"Id": int(workspace)} if workspace.isdigit() else {"Name": workspace}


def niri_event_name(variant: str) -> str:
    """Convert a Niri event variant to a Pyprland handler name.

    "WorkspacesChanged" becomes "event_niri_workspaces_changed", matching the
    `event_*` convention the manager uses to look up plugin handlers.

    Args:
        variant: The CamelCase event variant name

    Returns:
        The handler name plugins are expected to define
    """
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", variant).lower()
    return f"event_niri_{snake}"


def niri_variant_name(command: str | dict | list) -> str | dict | list:
    """Return the CamelCase variant name for a Niri request.

    Niri request variants are CamelCase: "outputs" -> "Outputs".
    Non-string payloads (lists/dicts) are returned unchanged.

    Args:
        command: The command or variant name to convert
    """
    if isinstance(command, str):
        return command[:1].upper() + command[1:]
    return command


def unwrap_niri_response(response: JSONResponse, variant: str | dict | list) -> Any:
    """Extract the payload from a Niri response, raising on failure.

    Niri wraps successful results in an "Ok" envelope, and the payload is
    further wrapped in the matching variant: {"Ok": {"Outputs": ...}}.

    Args:
        response: Raw JSON response from Niri
        variant: The request variant used (to locate the wrapped payload)
    """
    if not isinstance(response, dict) or "Ok" not in response:
        msg = f"Niri command failed: {response}"
        raise RuntimeError(msg)
    payload = response["Ok"]
    if isinstance(payload, dict) and len(payload) == 1 and variant in payload:
        return payload[variant]
    return payload


class NiriBackend(EnvironmentBackend):
    """Niri backend implementation."""

    address_prefix = ""
    """Niri identifies windows by plain integer ids, with no prefix."""

    minimum_address_length = 1
    """Window ids start at 1, so a single digit is a valid address."""

    scratch_workspace_prefix = "pypr-S-"
    """Niri has no special workspaces, so hidden scratchpads park on a named one."""

    scratch_workspaces_are_implicit = False
    """Niri only knows named workspaces declared in its config file.

    Moving a window to an undeclared name returns success but does nothing, so
    the plugin has to check for them up front rather than discover the silent
    failure at runtime.
    """

    supports_window_rules = False

    supports_offscreen_placement = False
    """Niri has no runtime config mutation, so rules can't be declared on the fly."""

    def is_hidden_workspace(self, name: str) -> bool:
        """Whether a workspace is one the user never sees directly.

        Niri has no special workspaces, so only the ones Pyprland parks
        scratchpads on count.

        Args:
            name: The workspace name

        Returns:
            True if the workspace is hidden
        """
        return name.startswith(self.scratch_workspace_prefix)

    async def missing_scratch_workspaces(self, uids: Iterable[str], *, log: Logger) -> list[str]:
        """Return the parking workspaces that are not declared in the config.

        Args:
            uids: Scratchpad identifiers
            log: Logger to use for this operation

        Returns:
            The names the user still has to declare, in order
        """
        try:
            workspaces = cast("list[dict]", await self.execute_json("workspaces", log=log))
        except (OSError, ConnectionError, RuntimeError, json.JSONDecodeError) as e:
            log.warning("Could not check Niri workspaces: %s", e)
            return []
        declared = {ws.get("name") for ws in workspaces if ws.get("name")}
        return [name for uid in uids if (name := self.scratch_workspace(uid)) not in declared]

    def __init__(self, state: SharedState) -> None:
        """Initialize the backend and its monitor mapping cache.

        Args:
            state: Shared state object
        """
        super().__init__(state)
        # Populated from the event stream, or lazily queried when no event has
        # been seen yet. `None` means "unknown", not "empty".
        self._workspace_outputs: dict[int, str] | None = None
        self._monitor_ids: dict[str, int] | None = None
        # State backing the synthesised events. Niri reports current state, not
        # transitions, so these hold the previous state to diff against.
        self._known_windows: dict[int, bool] = {}  # window id -> is_floating
        self._known_outputs: set[str] = set()

    def parse_events(self, raw_data: str, *, log: Logger) -> list[tuple[str, Any]]:
        """Parse a raw event string into the raw event plus any synthesised ones.

        Niri reports state, not transitions. Three things plugins need have no
        native event, so they are derived here from the previous state rather
        than in each plugin:

        - `event_niri_window_opened`: `WindowOpenedOrChanged` fires repeatedly
          for the same window (map, then title changes), so only the first
          sighting of an id is an open.
        - `event_niri_window_floating_changed`: niri has no floating event; the
          change is visible only as a flipped `is_floating`.
        - `event_niri_monitor_added` / `..._removed`: niri has no monitor event
          at all. `WorkspacesChanged` is a complete replacement, so the set of
          distinct outputs in it is the current output set.

        Args:
            raw_data: Raw event string from the compositor
            log: Logger to use for this operation

        Returns:
            The raw event followed by any synthesised events
        """
        event = self.parse_event(raw_data, log=log)
        if not event:
            return []
        name, data = event
        return [event, *self._synthesize(name, data)]

    def _synthesize(self, name: str, data: dict[str, Any]) -> list[tuple[str, Any]]:
        """Derive the events Niri doesn't send natively.

        Args:
            name: The handler name of the raw event
            data: The raw event payload

        Returns:
            Additional events to dispatch after the raw one
        """
        if name == "event_niri_window_opened_or_changed":
            return self._diff_window(data.get("window") or {})
        if name == "event_niri_windows_changed":
            # Full replacement: rebuild the table without reporting every
            # window as newly opened.
            self._known_windows = {w["id"]: w.get("is_floating", False) for w in data.get("windows", []) if "id" in w}
            return []
        if name == "event_niri_window_closed":
            self._known_windows.pop(data.get("id"), None)
            return []
        if name == "event_niri_workspaces_changed":
            return self._diff_outputs(data.get("workspaces", []))
        return []

    def _diff_window(self, window: dict[str, Any]) -> list[tuple[str, Any]]:
        """Split a WindowOpenedOrChanged into open and floating-change events."""
        window_id = window.get("id")
        if window_id is None:
            return []
        floating = window.get("is_floating", False)

        if window_id not in self._known_windows:
            self._known_windows[window_id] = floating
            return [("event_niri_window_opened", window)]

        events: list[tuple[str, Any]] = []
        if self._known_windows[window_id] != floating:
            events.append(("event_niri_window_floating_changed", window))
        self._known_windows[window_id] = floating
        return events

    def _diff_outputs(self, workspaces: list[dict[str, Any]]) -> list[tuple[str, Any]]:
        """Derive monitor add/remove from the replaced workspace configuration."""
        outputs = {ws["output"] for ws in workspaces if ws.get("output")}
        if outputs == self._known_outputs:
            return []

        # The first WorkspacesChanged is the initial snapshot, not a change.
        known, self._known_outputs = self._known_outputs, outputs
        if not known:
            return []

        return [
            *(("event_niri_monitor_added", {"output": name}) for name in sorted(outputs - known)),
            *(("event_niri_monitor_removed", {"output": name}) for name in sorted(known - outputs)),
        ]

    def parse_event(self, raw_data: str, *, log: Logger) -> tuple[str, Any] | None:
        """Parse a raw event string into (event_name, event_data).

        Niri emits one JSON object per line, shaped as a single-key envelope:
        `{"WorkspacesChanged": {...}}`.

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

        if not isinstance(event, dict) or len(event) != 1:
            return None
        variant, data = next(iter(event.items()))
        if not isinstance(data, dict):
            return None

        self._update_cache(variant, data)
        return niri_event_name(variant), data

    def _update_cache(self, variant: str, data: dict[str, Any]) -> None:
        """Keep the monitor mapping in sync with the event stream.

        `WorkspacesChanged` carries the full workspace list, so the mapping can
        be rebuilt outright instead of being invalidated and re-queried.

        Args:
            variant: The event variant name
            data: The event payload
        """
        if variant == "WorkspacesChanged":
            self._workspace_outputs = {ws["id"]: ws.get("output") or "" for ws in data.get("workspaces", []) if "id" in ws}
        elif variant == "ConfigLoaded":
            # Output configuration may have changed under us.
            self._monitor_ids = None

    async def execute(self, command: str | list | dict, *, log: Logger, **kwargs: Any) -> bool:
        """Execute a command (or list of commands).

        Args:
            command: The command to execute
            log: Logger to use for this operation
            **kwargs: Additional arguments (weak, etc.)
        """
        weak = kwargs.get("weak", False)
        # Niri commands are structured objects/lists, not a Hyprland-style command line.
        try:
            ret = await niri_request(command, logger=log)
            if isinstance(ret, dict) and "Ok" in ret:
                return True
        except (OSError, ConnectionError, json.JSONDecodeError) as e:
            log.warning("Niri command %r failed: %s", command, e)
            return False

        if weak:
            log.warning("Niri command %r failed: %s", command, ret)
        else:
            log.error("Niri command %r failed: %s", command, ret)
        return False

    async def execute_json(self, command: str, *, log: Logger, **kwargs: Any) -> Any:
        """Execute a command and return the JSON result.

        Plugins ask for "clients" using Hyprland's vocabulary and expect
        Hyprland-shaped dicts back, so that request is served from
        `get_clients` rather than passed through as an unknown variant.

        Args:
            command: The command to execute
            log: Logger to use for this operation
            **kwargs: Additional arguments
        """
        if command == "clients":
            return await self.get_clients(mapped=False, log=log)
        request = niri_variant_name(command)
        return unwrap_niri_response(await niri_request(request, logger=log), request)

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
        windows = cast("list[dict]", await self.execute_json("windows", log=log))
        workspace_outputs, ids = await self._monitor_mapping(log=log)
        return [
            self._map_niri_client(client, workspace_outputs, ids)
            for client in windows
            if (not mapped or client.get("is_mapped", True))
            and (workspace is None or str(client.get("workspace_id")) == workspace)
            and (workspace_bl is None or str(client.get("workspace_id")) != workspace_bl)
        ]

    async def _monitor_mapping(self, *, log: Logger) -> tuple[dict[int, str], dict[str, int]]:
        """Resolve where each workspace lives and how outputs map to monitor ids.

        Both halves are cached: the workspace mapping is normally refreshed by
        `WorkspacesChanged` events (no IPC), and the output ids are re-queried
        only on a new output name (hotplug) or a config reload.

        Returns:
            A (workspace id -> output name, output name -> monitor id) pair,
            both empty if Niri could not be queried.
        """
        try:
            if self._workspace_outputs is None:
                workspaces = cast("list[dict]", await self.execute_json("workspaces", log=log))
                self._workspace_outputs = {ws["id"]: ws.get("output") or "" for ws in workspaces if "id" in ws}

            known = self._monitor_ids
            if known is None or any(name and name not in known for name in self._workspace_outputs.values()):
                outputs = cast("dict[str, Any]", await self.execute_json("outputs", log=log))
                self._monitor_ids = monitor_ids(outputs)
        except (OSError, ConnectionError, RuntimeError, json.JSONDecodeError) as e:
            log.warning("Could not resolve Niri monitors: %s", e)
            return self._workspace_outputs or {}, self._monitor_ids or {}

        return self._workspace_outputs, self._monitor_ids

    def _map_niri_client(
        self,
        niri_client: dict[str, Any],
        workspace_outputs: dict[int, str] | None = None,
        ids: dict[str, int] | None = None,
    ) -> ClientInfo:
        """Helper to map Niri window dict to ClientInfo TypedDict.

        Args:
            niri_client: A window entry from Niri's "Windows" response
            workspace_outputs: Mapping of workspace id to output name, used to
                resolve the window's monitor
            ids: Mapping of output name to synthetic monitor id
        """
        layout = niri_client.get("layout") or {}
        # Only floating windows have a position within the workspace view;
        # tiled ones report null and are reported at the origin.
        position = layout.get("tile_pos_in_workspace_view") or (0, 0)
        size = layout.get("window_size") or (0, 0)

        output = (workspace_outputs or {}).get(cast("int", niri_client.get("workspace_id")), "")
        monitor = (ids or {}).get(output, -1)

        return cast(
            "ClientInfo",
            {
                "address": str(niri_client.get("id")),
                "class": niri_client.get("app_id"),
                "title": niri_client.get("title"),
                "workspace": {"name": str(niri_client.get("workspace_id"))},
                "pid": niri_client.get("pid") or -1,
                "mapped": niri_client.get("is_mapped", True),
                "hidden": False,
                "at": (int(position[0]), int(position[1])),
                "size": (int(size[0]), int(size[1])),
                "floating": niri_client.get("is_floating", False),
                "monitor": monitor,
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

    async def get_monitors(self, *, log: Logger, include_disabled: bool = False) -> list[MonitorInfo]:
        """Return the list of monitors.

        Args:
            log: Logger to use for this operation
            include_disabled: Ignored for Niri (no concept of disabled monitors)
        """
        outputs = await self.execute_json("outputs", log=log)
        ids = monitor_ids(outputs)
        # Order the list by the same key the ids use, so position and id agree.
        monitors = [niri_output_to_monitor_info(name, outputs[name], ids[name]) for name in sorted(outputs)]
        await self._attach_active_workspaces(monitors, log=log)
        return monitors

    async def _attach_active_workspaces(self, monitors: list[MonitorInfo], *, log: Logger) -> None:
        """Fill in each monitor's active workspace and focus state.

        Niri reports outputs and workspaces separately, but callers expect the
        Hyprland shape where a monitor carries its active workspace and a focus
        flag. Focus is a property of a workspace in Niri, so the focused monitor
        is the one hosting the focused workspace.

        Args:
            monitors: The monitors to annotate, modified in place
            log: Logger to use for this operation
        """
        try:
            workspaces = cast("list[dict]", await self.execute_json("workspaces", log=log))
        except (OSError, ConnectionError, RuntimeError, json.JSONDecodeError) as e:
            log.warning("Could not resolve Niri active workspaces: %s", e)
            return

        active = {ws["output"]: ws for ws in workspaces if ws.get("is_active") and ws.get("output")}
        focused_output = next((ws["output"] for ws in workspaces if ws.get("is_focused") and ws.get("output")), None)

        for monitor in monitors:
            workspace = active.get(monitor["name"])
            if workspace:
                monitor["activeWorkspace"] = {
                    "id": workspace["id"],
                    # Niri workspaces are usually unnamed; the id stands in,
                    # matching how clients report their workspace.
                    "name": workspace.get("name") or str(workspace["id"]),
                }
            monitor["focused"] = monitor["name"] == focused_output

    async def execute_batch(self, commands: list[str], *, log: Logger) -> None:
        """Execute a batch of commands.

        Args:
            commands: List of commands to execute
            log: Logger to use for this operation
        """
        # Niri has no batch protocol, so each command is sent individually.
        for cmd in commands:
            await self.execute(["action", cmd], log=log)

    def get_default_notifier(self) -> Notifier:
        """Return notify-send notifier (Niri has no native notification IPC)."""
        return NotifySendNotifier()

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
        silent: bool = True,
        log: Logger,
    ) -> bool:
        """Move a window to a workspace.

        Niri requires an explicit `focus` field; Hyprland's `silent` (don't
        follow the window) is its inverse.

        Args:
            address: Window ID
            workspace: Target workspace ID or name
            silent: If True, don't follow the window to its new workspace
            log: Logger to use for this operation
        """
        return await self.execute(
            {
                "Action": {
                    "MoveWindowToWorkspace": {
                        "window_id": int(address),
                        "reference": niri_workspace_reference(workspace),
                        "focus": not silent,
                    }
                }
            },
            log=log,
        )

    async def pin_window(self, address: str, *, log: Logger) -> bool:
        """Toggle pin state - not available in Niri.

        Niri has no concept of a window pinned across workspaces. The closest
        equivalent for scratchpad-style windows is the floating layer, which is
        exposed through `toggle_floating` instead.

        Args:
            address: Window ID (unused)
            log: Logger to use for this operation
        """
        log.debug("pin_window: not available in Niri")
        return False

    async def close_window(self, address: str, *, silent: bool = True, log: Logger) -> bool:
        """Close a window by ID.

        Args:
            address: Window ID
            silent: Accepted for API consistency (currently unused for close)
            log: Logger to use for this operation
        """
        return await self.execute({"Action": {"CloseWindow": {"id": int(address)}}}, log=log)

    async def resize_window(self, address: str, width: int, height: int, *, log: Logger) -> bool:
        """Resize a window to exact pixel dimensions.

        Niri sizes windows through separate width and height actions, each
        taking a `SizeChange`. Both must succeed for the resize to count.

        Args:
            address: Window ID
            width: Target width in pixels
            height: Target height in pixels
            log: Logger to use for this operation
        """
        window_id = int(address)
        results = [
            await self.execute(
                {"Action": {"SetWindowWidth": {"id": window_id, "change": {"SetFixed": width}}}},
                log=log,
            ),
            await self.execute(
                {"Action": {"SetWindowHeight": {"id": window_id, "change": {"SetFixed": height}}}},
                log=log,
            ),
        ]
        return all(results)

    async def _output_origin(self, address: str, *, log: Logger) -> tuple[int, int]:
        """Return the logical origin of the output hosting a window.

        Args:
            address: Window ID
            log: Logger to use for this operation
        """
        try:
            windows = cast("list[dict]", await self.execute_json("windows", log=log))
            workspace_id = next((w["workspace_id"] for w in windows if str(w["id"]) == str(address)), None)
            if workspace_id is None:
                return (0, 0)
            workspaces = cast("list[dict]", await self.execute_json("workspaces", log=log))
            output = next((ws.get("output") for ws in workspaces if ws["id"] == workspace_id), None)
            if not output:
                return (0, 0)
            outputs = cast("dict[str, dict]", await self.execute_json("outputs", log=log))
            logical = (outputs.get(output) or {}).get("logical") or {}
        except (OSError, ConnectionError, RuntimeError, KeyError, json.JSONDecodeError) as e:
            log.warning("Could not resolve the output of window %s: %s", address, e)
            return (0, 0)
        return (logical.get("x", 0), logical.get("y", 0))

    async def move_window(self, address: str, x: int, y: int, *, log: Logger) -> bool:
        """Move a window to an exact position on screen.

        Only meaningful for floating windows; tiled ones are positioned by the
        layout and the request is ignored. Callers use Hyprland's global
        coordinate space, but Niri positions floating windows relative to their
        output's working area, so the monitor origin is subtracted first.

        Args:
            address: Window ID
            x: Target x position in pixels
            y: Target y position in pixels
            log: Logger to use for this operation
        """
        origin_x, origin_y = await self._output_origin(address, log=log)
        return await self.execute(
            {
                "Action": {
                    "MoveFloatingWindow": {
                        "id": int(address),
                        "x": {"SetFixed": float(x - origin_x)},
                        "y": {"SetFixed": float(y - origin_y)},
                    }
                }
            },
            log=log,
        )

    async def toggle_floating(self, address: str, *, log: Logger) -> bool:
        """Toggle floating state of a window.

        Args:
            address: Window ID
            log: Logger to use for this operation
        """
        return await self.execute({"Action": {"ToggleWindowFloating": {"id": int(address)}}}, log=log)

    async def set_window_floating(self, address: str, floating: bool, *, log: Logger) -> bool:
        """Move a window to the floating or the tiling layout.

        Unlike `toggle_floating` this is idempotent, which is what callers
        placing a window (such as scratchpads) actually need.

        Args:
            address: Window ID
            floating: True to float the window, False to tile it
            log: Logger to use for this operation
        """
        action = "MoveWindowToFloating" if floating else "MoveWindowToTiling"
        return await self.execute({"Action": {action: {"id": int(address)}}}, log=log)

    async def set_keyword(self, keyword_command: str, *, log: Logger) -> bool:
        """Execute a keyword command - not available in Niri.

        Niri has no runtime configuration mutation; rules must be declared in
        the config file ahead of time.

        Args:
            keyword_command: The keyword command (unused)
            log: Logger to use for this operation
        """
        log.debug("set_keyword: not available in Niri")
        return False

    # ─── Batch Window Operations (Niri overrides) ─────────────────────────────

    async def move_windows(self, placements: Iterable[tuple[str, int, int]], *, log: Logger) -> bool:
        """Move several windows to exact positions.

        Niri has no batch protocol, so these are issued one at a time.

        Args:
            placements: (address, x, y) triples
            log: Logger to use for this operation
        """
        results = [await self.move_window(addr, x, y, log=log) for addr, x, y in placements]
        return all(results)

    async def move_windows_to_workspace(
        self,
        addresses: Iterable[str],
        workspace: str,
        *,
        silent: bool = True,
        log: Logger,
    ) -> bool:
        """Move several windows to a workspace.

        Args:
            addresses: Window ids
            workspace: Target workspace ID
            silent: Ignored in Niri
            log: Logger to use for this operation
        """
        results = [await self.move_window_to_workspace(addr, workspace, silent=silent, log=log) for addr in addresses]
        return all(results)

    async def raise_windows(self, addresses: Iterable[str], *, log: Logger) -> bool:
        """Raise windows - not available in Niri.

        Niri manages stacking itself; focusing a floating window already brings
        it to the front, which covers the scratchpad use case.

        Args:
            addresses: Window ids (unused)
            log: Logger to use for this operation
        """
        log.debug("raise_windows: not available in Niri")
        return False

    async def set_window_animations(self, addresses: Iterable[str], enabled: bool, *, log: Logger) -> bool:
        """Toggle per-window animations - not available in Niri.

        This relies on Hyprland's window tags plus a matching runtime rule,
        neither of which Niri has. Callers degrade to a visible jump when
        pre-positioning a window.

        Args:
            addresses: Window ids (unused)
            enabled: Desired state (unused)
            log: Logger to use for this operation
        """
        log.debug("set_window_animations: not available in Niri")
        return False

    async def move_workspace_to_monitor(self, workspace: str, monitor: str, *, log: Logger) -> bool:
        """Move a whole workspace to another monitor.

        Args:
            workspace: Workspace name or ID
            monitor: Target output name
            log: Logger to use for this operation
        """
        return await self.execute(
            {"Action": {"MoveWorkspaceToMonitor": {"reference": niri_workspace_reference(workspace), "output": monitor}}},
            log=log,
        )
