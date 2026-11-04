# Niri event mapping

Working notes for porting event-driven plugins (scratchpads first) to Niri.

Verified against **niri 26.04 (`niri-ipc` 26.4.0)** by capturing the live event
stream while driving the compositor through each transition. Event payloads
below are abridged from real captures.

## Shape

Niri emits one JSON object per line on the `EventStream` socket, as a
single-key envelope:

```json
{"WindowFocusChanged": {"id": 15}}
```

`NiriBackend.parse_event` converts the variant to the `event_*` handler naming
the manager looks up, so `WorkspacesChanged` dispatches to
`event_niri_workspaces_changed`. The payload is passed through as a `dict`,
unlike Hyprland where handlers receive a raw comma-joined string.

**This differs from Hyprland handlers and is a porting hazard.** Hyprland's
`event_openwindow` receives `"ADDR,WORKSPACE,CLASS,TITLE"` and parses it by
hand; the niri equivalent receives a structured `dict`. Shared handlers need
either two entry points or a normalisation step.

## The 19 events

| Event | Payload | Relevant |
|---|---|---|
| `WorkspacesChanged` | `workspaces: [Workspace]` | ✅ full replace |
| `WorkspaceUrgencyChanged` | `id`, `urgent` | — |
| `WorkspaceActivated` | `id`, `focused` | ✅ |
| `WorkspaceActiveWindowChanged` | `workspace_id`, `active_window_id` | — |
| `WindowsChanged` | `windows: [Window]` | ✅ full replace |
| `WindowOpenedOrChanged` | `window: Window` | ✅ overloaded |
| `WindowClosed` | `id` | ✅ |
| `WindowFocusChanged` | `id: Option<u64>` | ✅ |
| `WindowFocusTimestampChanged` | `id`, `focus_timestamp` | — debounced |
| `WindowUrgencyChanged` | `id`, `urgent` | — |
| `WindowLayoutsChanged` | `changes: [(id, WindowLayout)]` | ✅ geometry |
| `KeyboardLayoutsChanged` | `keyboard_layouts` | — |
| `KeyboardLayoutSwitched` | `idx` | — |
| `OverviewOpenedOrClosed` | `is_open` | — niri-only |
| `ConfigLoaded` | `failed` | ✅ |
| `ScreenshotCaptured` | `path` | — |
| `CastsChanged` / `CastStartedOrChanged` / `CastStopped` | — | — |

## Mapping to the Hyprland handlers plugins use

| Hyprland handler | Niri source | Fidelity |
|---|---|---|
| `event_configreloaded` | `ConfigLoaded` | **1:1.** Also sent on connect, carries `failed`. |
| `event_closewindow(addr)` | `WindowClosed.id` | **1:1.** |
| `event_activewindowv2(addr)` | `WindowFocusChanged.id` | **1:1**, but `id` is nullable — "nothing focused" has no Hyprland equivalent. |
| `event_workspace(name)` | `WorkspaceActivated` where `focused == true` | **Close.** Niri distinguishes *active on its output* from *focused*; only the latter matches Hyprland. Niri workspaces are usually unnamed, so the id must be used as the name — matching what `_map_niri_client` already does. |
| `event_openwindow(addr,ws,cls,title)` | `WindowOpenedOrChanged` | **Needs state.** See below. |
| `event_changefloatingmode(addr,0/1)` | `WindowOpenedOrChanged` | **Needs state.** See below. |
| `event_monitoradded(name)` | *none* | **Must be derived.** See below. |
| `event_monitorremoved(name)` | *none* | **Must be derived.** |

## The three that need synthesis

### 1. Open vs. change

`WindowOpenedOrChanged` covers both, and fires repeatedly for one window.
Captured while spawning a terminal:

```
WindowOpenedOrChanged   {"window": {"id": 16, "title": "kitty", "app_id": "PYPRTEST", ...}}
WindowLayoutsChanged    ...
WindowOpenedOrChanged   {"window": {"id": 16, "title": "sleep",  "app_id": "PYPRTEST", ...}}
```

Two events for one window — the second is a title change. Emitting
`event_openwindow` for both would double-fire scratchpad adoption.

**Needs:** a set of known window ids in the adapter. First sighting →
`openwindow`; later sightings → a change event. `WindowClosed` and the
`WindowsChanged` full-replace both prune the set.

This is also the hook for the step-5 positioning work, since it is the only
point where a newly mapped window can be caught.

### 2. Floating mode

Niri has no floating-mode event. Captured while floating and re-tiling a
window, the only window-level signal was:

```
### float a window
WindowOpenedOrChanged   {"window": {"id": 2, ..., "is_floating": true}}
WindowLayoutsChanged    {"changes": [[2, {"pos_in_scrolling_layout": null, ...}]]}

### tile it back
WindowOpenedOrChanged   {"window": {"id": 2, ..., "is_floating": false}}
WindowLayoutsChanged    {"changes": [[2, {"pos_in_scrolling_layout": [2,1], ...}]]}
```

**Needs:** previous `is_floating` per window id, diffed on every
`WindowOpenedOrChanged`. Same state table as above, so one structure serves
both: `id -> (is_floating, ...)`.

Note `pos_in_scrolling_layout` is `null` exactly when a window is floating,
which is a usable cross-check.

### 3. Monitor add/remove

Niri has no monitor event at all. `WorkspacesChanged` is the proxy: workspaces
are bound to outputs and the payload is a **complete replacement**, so the set
of distinct `output` values is the current output set. Diffing it across
consecutive events yields added and removed monitors.

The adapter already caches this mapping for `get_clients`
(`_update_cache`), so the diff costs nothing extra — it is the same data,
already arriving.

**Caveat, unverified:** I did not test physically disconnecting an output,
since that would have disturbed the running session. The derivation follows
from the documented "completely replaces the previous configuration"
semantics, but should be confirmed on a disposable session before relying on
it for `monitorremoved`.

## Geometry

`WindowLayoutsChanged` is the only event for a pure move or resize — a
floating window moved with `MoveFloatingWindow` produced **no**
`WindowOpenedOrChanged`. Hyprland has no equivalent event; plugins poll
instead. For scratchpads this is an upgrade: animation state can follow the
compositor rather than re-query after each step.

## Protocol gotchas found while implementing

Verified against the live socket; each of these returns a misleading result
rather than an obvious error.

- **`MoveWindowToWorkspace` requires `focus`.** Omitting it yields
  `{"Err": "error parsing request"}`. The adapter had always omitted it, so
  this call never worked on Niri. Hyprland's `silent` is its inverse.
- **Workspace references are `{"Id": n}` or `{"Name": s}`.** Scratchpads park
  on named workspaces, so assuming a numeric id raises `ValueError`.
- **Moves to an undeclared workspace name silently succeed.** The reply is
  `{"Ok": "Handled"}` and nothing happens. Named workspaces only exist if
  declared in the config file.
- **Index references clamp.** `{"Index": 9}` with three workspaces lands on
  the last one rather than creating any, so it can't be used to reach a
  scratch area.

## Niri cannot hide windows

Checked against all 141 `Action` variants: there is no `Hide`, `Minimize`,
`Iconify` or equivalent, and no special-workspace concept.

Off-screen parking doesn't work either — Niri clamps floating windows so a
sliver always stays visible:

| Requested | Actual |
|---|---|
| `(-5000, 0)` | `(-625, 34)` |
| `(99999, 99999)` | `(3365, 1365)` |
| `(-200, -200)` | `(-200, -166)` |

So moving a window to another workspace is the only mechanism available. The
consequence is that a hidden scratchpad lives on an ordinary workspace in the
output's scroll order and can be scrolled past, unlike Hyprland's genuinely
out-of-band special workspaces. Fixing that properly needs an upstream change
(a hide action, or a workspace flag excluding it from the scroll order).

## Window rules

Niri has no runtime config mutation, so `windowrule` equivalents can't be
declared for a window that doesn't exist yet. Of the four rules scratchpads
set, three already have imperative counterparts applied elsewhere:

| Rule | Niri counterpart |
|---|---|
| `workspace ... silent` | `Scratch.initialize` moves the window |
| `size` / `move` | `_fix_size` and `_show_transition`, on every show |
| `group deny` | not needed; Niri doesn't auto-group |
| `float` | **nothing** — applied reactively by `apply_initial_state` |

Only `float` needed a new path. Because it runs after the window maps rather
than before, Niri shows a brief flash of the window tiled in its default
position. That is inherent to the lack of pre-map rules.

## Suggested shape

The open/change, floating-mode and monitor derivations all need the same
thing: previous state, maintained from the stream. That argues for a small
synthesis layer in `NiriBackend`, extending `_update_cache`, which already
tracks workspace→output for `get_clients`:

```
_known_windows: dict[int, bool]   # id -> is_floating
_known_outputs: set[str]
```

Keeping it in the adapter — rather than in each plugin — means plugins keep
receiving one event per logical change, and `environments=[HYPRLAND, NIRI]`
becomes a matter of handler naming rather than per-plugin state machines.

This is what was implemented: `NiriBackend` synthesises
`event_niri_window_opened`, `event_niri_window_floating_changed`,
`event_niri_monitor_added` and `event_niri_monitor_removed`, and the plugins
implement `event_niri_*` handlers alongside their Hyprland ones. Both delegate
to shared `_on_*` cores so the logic exists once.

## Still unverified

The `monitor_added` / `monitor_removed` derivation is covered by unit tests
but has never been exercised against a real hotplug, because disconnecting an
output moves windows between monitors with no way to put them back. It should
be confirmed on a disposable session before anything depends on it.
