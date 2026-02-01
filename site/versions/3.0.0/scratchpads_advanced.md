---
---
# Fine tuning scratchpads

> [!note]
> For basic setup, see [Scratchpads](./scratchpads).

Advanced configuration options

| Option | Description |
|--------|-------------|
| `offset` · *str* · =`"100%"` | Hide animation distance |
| `pinned` · *bool* · =`true` | Sticky to monitor |
| `unfocus` · *str* | Action on unfocus ('hide' or empty) |
| `hysteresis` · *float* · =`0.4` | Delay before unfocus hide |
| `excludes` · *list* | Scratches to hide when shown |
| `restore_excluded` · *bool* · =`false` | Restore excluded on hide |
| `preserve_aspect` · *bool* · =`false` | Keep size/position across shows |
| `hide_delay` · *float* · =`0.0` | Delay before hide animation |
| `force_monitor` · *str* | Always show on specific monitor |
| `alt_toggle` · *bool* · =`false` | Alternative toggle for multi-monitor |
| `allow_special_workspaces` · *bool* · =`true` | Allow over special workspaces |
| `smart_focus` · *bool* · =`true` | Restore focus on hide |
| `close_on_hide` · *bool* · =`false` | Close instead of hide |
| `use` · *str* | Inherit from another scratchpad definition |
| `monitor` · *dict* | Per-monitor config overrides |


### `use` *str* {#config-use}

List of scratchpads (or single string) that will be used for the default values of this scratchpad.
Think about *templates*:

```toml
[scratchpads.terminals]
animation = "fromTop"
margin = 50
size = "75% 60%"
max_size = "1920px 100%"

[scratchpads.term]
command = "kitty --class kitty-dropterm"
class = "kitty-dropterm"
use = "terminals"
```

### `pinned` *bool* · =`true` {#config-pinned}

Makes the scratchpad "sticky" to the monitor, following any workspace change.

### `excludes` *list* {#config-excludes}

List of scratchpads to hide when this one is displayed, eg: `excludes = ["term", "volume"]`.
If you want to hide every displayed scratch you can set this to the string `"*"` instead of a list: `excludes = "*"`.

### `restore_excluded` *bool* · =`false` {#config-restore-excluded}

When enabled, will remember the scratchpads which have been closed due to `excludes` rules, so when the scratchpad is hidden, those previously hidden scratchpads will be shown again.

### `unfocus` *str* {#config-unfocus}

When set to `"hide"`, allow to hide the window when the focus is lost.

Use `hysteresis` to change the reactivity

### `hysteresis` *float* · =`0.4` {#config-hysteresis}

Controls how fast a scratchpad hiding on unfocus will react. Check `unfocus` option.
Set to `0` to disable.

> [!important]
> Only relevant when `unfocus="hide"` is used.

### `preserve_aspect` *bool* · =`false` {#config-preserve-aspect}

When set to `true`, will preserve the size and position of the scratchpad when called repeatedly from the same monitor and workspace even though an `animation` , `position` or `size` is used (those will be used for the initial setting only).

Forces the `lazy` option.

### `offset` *str* · =`"100%"` {#config-offset}

Number of pixels for the **hide** sliding animation (how far the window will go).

> [!tip]
> - It is also possible to set a string to express percentages of the client window
> - `margin` is automatically added to the offset

### `hide_delay` *float* · =`0.0` {#config-hide-delay}

Delay (in seconds) after which the hide animation happens, before hiding the scratchpad.

Rule of thumb, if you have an animation with speed "7", as in:
```bash
    animation = windowsOut, 1, 7, easeInOut, popin 80%
```
You can divide the value by two and round to the lowest value, here `3`, then divide by 10, leading to `hide_delay = 0.3`.

### `force_monitor` *str* {#config-force-monitor}

If set to some monitor name (eg: `"DP-1"`), it will always use this monitor to show the scratchpad.

### `alt_toggle` *bool* · =`false` {#config-alt-toggle}

When enabled, use an alternative `toggle` command logic for multi-screen setups.
It applies when the `toggle` command is triggered and the toggled scratchpad is visible on a screen which is not the focused one.

Instead of moving the scratchpad to the focused screen, it will hide the scratchpad.

### `allow_special_workspaces` *bool* · =`true` {#config-allow-special-workspaces}

When enabled, you can toggle a scratchpad over a special workspace.
It will always use the "normal" workspace otherwise.

> [!note]
> Can't be disabled when using *Hyprland* < 0.39 where this behavior can't be controlled.

### `smart_focus` *bool* · =`true` {#config-smart-focus}

When enabled, the focus will be restored in a best effort way as an attempt to improve the user experience.
If you face issues such as spontaneous workspace changes, you can disable this feature.


### `close_on_hide` *bool* · =`false` {#config-close-on-hide}

When enabled, the window in the scratchpad is closed instead of hidden when `pypr hide <name>` is run.
This option implies `lazy = true`.
This can be useful on laptops where background apps may increase battery power draw.

Note: Currently this option changes the hide animation to use hyprland's close window animation.

### `monitor` *dict* {#config-monitor}

Per-monitor configuration overrides. Most display-related attributes can be changed (not `command`, `class` or `process_tracking`).

Use the `monitor.<monitor name>` configuration item to override values, eg:

```toml
[scratchpads.music.monitor.eDP-1]
position = "30% 50%"
animation = "fromBottom"
```

You may want to inline it for simple cases:

```toml
[scratchpads.music]
monitor = {HDMI-A-1={size = "30% 50%"}}
```
