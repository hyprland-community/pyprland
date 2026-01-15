# Plan for Supporting Niri Monitor Events and Data

This plan outlines the steps to enable monitor management support for Niri in Pyprland, specifically focusing on the `wallpapers` plugin as the primary target, while laying the groundwork for other plugins.

## 1. Core Event Loop Update (`pyprland/command.py`)
Enable detection and handling of Niri's JSON events alongside Hyprland's IPC events.

-   **Modify `read_events_loop`**:
    -   Detect if an event line starts with `{`.
    -   Parse it as JSON.
    -   Extract the event type from `Variant.type` (e.g., `OutputsChanged`).
    -   Dispatch as `event_<Type>` passing the inner dictionary data.

## 2. IPC Abstraction Updates (`pyprland/ipc.py`)
Update core IPC utility functions to be environment-aware.

-   **Update `get_monitor_props`**:
    -   Add a branch for `if NIRI_SOCKET:`.
    -   Call `nirictl_json("outputs")`.
    -   Map the result to a `MonitorInfo` compatible structure (specifically handling `focused` state).
    -   Return the active monitor info.

## 3. Interface Updates (`pyprland/plugins/interface.py`)
Update the base plugin interface to support fetching clients on Niri.

-   **Update `get_clients`**:
    -   Add a branch for `self.state.environment == "niri"`.
    -   Call `self.nirictl_json("windows")`.
    -   Implement a basic mapping from Niri window objects to `ClientInfo` (id -> address, app_id -> class, etc.) to satisfy basic plugin needs.

## 4. Wallpapers Plugin Update (`pyprland/plugins/wallpapers/__init__.py`)
Update the wallpapers plugin to work with Niri.

-   **Update `fetch_monitors`**:
    -   Add logic to check `extension.state.environment == "niri"`.
    -   If Niri, call `nirictl_json("outputs")`.
    -   **Crucial:** Map Niri's string transforms (e.g., "90", "flipped") to Hyprland's integer constants (0-7). This ensures the existing `imageutils.MonitorInfo` and `RoundedImageManager` logic works without modification.
-   **Add Event Handler**:
    -   Implement `async def event_OutputsChanged(self, _data)` which simply calls `self.next_background_event.set()`, effectively aliasing the existing `monitoradded` logic.

## 5. Other Plugin Adaptations (Deferred/Follow-up)
While the above enables `wallpapers`, other plugins (`monitors`, `shift_monitors`, `menubar`) require more significant refactoring because they currently rely on specific arguments (monitor names) passed in Hyprland events, whereas Niri's `OutputsChanged` is generic.

-   **Strategy**: Plugins should move from "Event(Item)" logic to "Event(Generic) -> Fetch State -> Diff" logic. This will be handled in future tasks.

## Verification
-   Run `pypr` with `NIRI_SOCKET` set.
-   Verify `wallpapers` plugin loads and fetches monitor list correctly.
-   Verify `OutputsChanged` event triggers a wallpaper refresh (e.g. by changing monitor config or re-plugging a screen).
