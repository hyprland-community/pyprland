# Fine tuning scratchpads

Advanced configuration options

## `pinned` (optional)

`true` by default

Makes the scratchpad "sticky" to the monitor, following any workspace change.

## `excludes` (optional)

No default value.

List of scratchpads to hide when this one is displayed, eg: `excludes = ["term", "volume"]`.
If you want to hide every displayed scratch you can set this to the string `"*"` instead of a list: `excludes = "*"`.

## `unfocus` (optional)

No default value.

When set to `"hide"`, allow to hide the window when the focus is lost.

Use `hysteresis` to change the reactivity

## `hysteresis` (optional)

Defaults to `0.4` (seconds)

Controls how fast a scratchpad hiding on unfocus will react. Check `unfocus` option.
Set to `0` to disable.

> [!important]
> Only relevant when `unfocus="hide"` is used.

## `margin` (optional)

default value is `60`.

number of pixels separating the scratchpad from the screen border, depends on the [animation](./scratchpads#animation) set.

> [!tip]
> It is also possible to set a string to express percentages of the screen (eg: '`3%`').

## `max_size` (optional)

No default value.

Same format as `size` (see above), only used if `size` is also set.

Limits the `size` of the window accordingly.
To ensure a window will not be too large on a wide screen for instance:

```toml
size = "60% 30%"
max_size = "1200px 100%"
```

## `lazy` (optional)

default to `false`.

when set to `true`, prevents the command from being started when pypr starts, it will be started when the scratchpad is first used instead.

- Good: saves resources when the scratchpad isn't needed
- Bad: slows down the first display (app has to launch before showing)

## `preserve_aspect` (optional)

Not set by default.
When set to `true`, will preserve the size and position of the scratchpad when called repeatedly from the same monitor and workspace even though an `animation` , `position` or `size` is used (those will be used for the initial setting only).

Forces the `lazy` option.

## `offset` (optional)

In pixels, default to `0` (client's window size + margin).

Number of pixels for the **hide** sliding animation (how far the window will go).

> [!tip]
> - It is also possible to set a string to express percentages of the client window
> - `margin` is automatically added to the offset
> - automatic (value not set) is same as `"100%"`

## `hide_delay` (optional)

Defaults to `0.2`

Delay (in seconds) after which the hide animation happens, before hiding the scratchpad.

Rule of thumb, if you have an animation with speed "7", as in:
```bash
    animation = windowsOut, 1, 7, easeInOut, popin 80%
```
You can divide the value by two and round to the lowest value, here `3`, then divide by 10, leading to `hide_delay = 0.3`.

## `restore_focus` (optional)

Enabled by default, set to `false` if you don't want the focused state to be restored when a scratchpad is hidden.

## `force_monitor` (optional)

If set to some monitor name (eg: `"DP-1"`), it will always use this monitor to show the scratchpad.

## `alt_toggle` (optional)

Default value is `false`

When enabled, use an alternative `toggle` command logic for multi-screen setups.
It applies when the `toggle` command is triggered and the toggled scratchpad is visible on a screen which is not the focused one.

Instead of moving the scratchpad to the focused screen, it will hide the scratchpad.

## `allow_special_workspaces` (optional)

Default value is `false` (can't be enabled when using *Hyprland* < 0.39 where this behavior can't be controlled and is disabled).

When enabled, you can toggle a scratchpad over a special workspace.
It will always use the "normal" workspace otherwise.

## `smart_focus` (optional)

Default value is `true`.

When enabled, the focus will be restored in a best effort way as en attempt to improve the user experience.
If you face issues such as spontaneous workspace changes, you can disable this feature.

