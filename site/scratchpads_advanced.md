---
---
# Fine tuning scratchpads

> [!note]
> For basic setup, see [Scratchpads](./scratchpads).

Advanced configuration options

<PluginConfig plugin="scratchpads" linkPrefix="config-" :filter="['use', 'pinned', 'excludes', 'restore_excluded', 'unfocus', 'hysteresis', 'preserve_aspect', 'offset', 'hide_delay', 'force_monitor', 'alt_toggle', 'allow_special_workspace', 'smart_focus', 'close_on_hide', 'monitor']" />

### `use` {#config-use}

<ConfigDefault plugin="scratchpads" option="use" />

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

### `pinned` {#config-pinned}

<ConfigDefault plugin="scratchpads" option="pinned" />

Makes the scratchpad "sticky" to the monitor, following any workspace change.

### `excludes` {#config-excludes}

<ConfigDefault plugin="scratchpads" option="excludes" />

List of scratchpads to hide when this one is displayed, eg: `excludes = ["term", "volume"]`.
If you want to hide every displayed scratch you can set this to the string `"*"` instead of a list: `excludes = "*"`.

### `restore_excluded` {#config-restore-excluded}

<ConfigDefault plugin="scratchpads" option="restore_excluded" />

When enabled, will remember the scratchpads which have been closed due to `excludes` rules, so when the scratchpad is hidden, those previously hidden scratchpads will be shown again.

### `unfocus` {#config-unfocus}

<ConfigDefault plugin="scratchpads" option="unfocus" />

When set to `"hide"`, allow to hide the window when the focus is lost.

Use `hysteresis` to change the reactivity

### `hysteresis` {#config-hysteresis}

<ConfigDefault plugin="scratchpads" option="hysteresis" />

Controls how fast a scratchpad hiding on unfocus will react. Check `unfocus` option.
Set to `0` to disable.

> [!important]
> Only relevant when `unfocus="hide"` is used.

### `preserve_aspect` {#config-preserve-aspect}

<ConfigDefault plugin="scratchpads" option="preserve_aspect" />

When set to `true`, will preserve the size and position of the scratchpad when called repeatedly from the same monitor and workspace even though an `animation` , `position` or `size` is used (those will be used for the initial setting only).

Forces the `lazy` option.

### `offset` {#config-offset}

<ConfigDefault plugin="scratchpads" option="offset" />

Number of pixels for the **hide** sliding animation (how far the window will go).

> [!tip]
> - It is also possible to set a string to express percentages of the client window
> - `margin` is automatically added to the offset
> - automatic (value not set) is same as `"100%"`

### `hide_delay` {#config-hide-delay}

<ConfigDefault plugin="scratchpads" option="hide_delay" />

Delay (in seconds) after which the hide animation happens, before hiding the scratchpad.

Rule of thumb, if you have an animation with speed "7", as in:
```bash
    animation = windowsOut, 1, 7, easeInOut, popin 80%
```
You can divide the value by two and round to the lowest value, here `3`, then divide by 10, leading to `hide_delay = 0.3`.

### `force_monitor` {#config-force-monitor}

<ConfigDefault plugin="scratchpads" option="force_monitor" />

If set to some monitor name (eg: `"DP-1"`), it will always use this monitor to show the scratchpad.

### `alt_toggle` {#config-alt-toggle}

<ConfigDefault plugin="scratchpads" option="alt_toggle" />

When enabled, use an alternative `toggle` command logic for multi-screen setups.
It applies when the `toggle` command is triggered and the toggled scratchpad is visible on a screen which is not the focused one.

Instead of moving the scratchpad to the focused screen, it will hide the scratchpad.

### `allow_special_workspace` {#config-allow-special-workspace}

<ConfigDefault plugin="scratchpads" option="allow_special_workspace" />

When enabled, you can toggle a scratchpad over a special workspace.
It will always use the "normal" workspace otherwise.

> [!note]
> Can't be disabled when using *Hyprland* < 0.39 where this behavior can't be controlled.

### `smart_focus` {#config-smart-focus}

<ConfigDefault plugin="scratchpads" option="smart_focus" />

When enabled, the focus will be restored in a best effort way as an attempt to improve the user experience.
If you face issues such as spontaneous workspace changes, you can disable this feature.


### `close_on_hide` {#config-close-on-hide}

<ConfigDefault plugin="scratchpads" option="close_on_hide" />

When enabled, the window in the scratchpad is closed instead of hidden when `pypr hide <name>` is run.
This option implies `lazy = true`.
This can be useful on laptops where background apps may increase battery power draw.

Note: Currently this option changes the hide animation to use hyprland's close window animation.

### `monitor` {#config-monitor}

<ConfigDefault plugin="scratchpads" option="monitor" />

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
