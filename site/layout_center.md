Implements a workspace layout where one window is bigger and centered,
other windows are tiled as usual in the background.

On `toggle`, the active window is made floating and centered if the layout wasn't enabled, else reverts the floating status.

With `next` and `prev` you can cycle the active window, keeping the same layout type.
If the layout_center isn't active and `next` or `prev` is used, it will call the "next" and "prev" configuration options.
To allow full override of the focus keys, `next2` and `prev2` are provided, they do the same actions as "next" and "prev" but allow different fallback commands.

Configuration sample:
```toml
[layout_center]
margin = 60
offset = [0, 30]
next = "movefocus r"
prev = "movefocus l"
next2 = "movefocus d"
prev2 = "movefocus u"
```

using the following in `hyprland.conf`:
```sh
bind = $mainMod, M, exec, pypr layout_center toggle # toggle the layout
# focus change keys
bind = $mainMod, left, exec, pypr layout_center prev
bind = $mainMod, right, exec, pypr layout_center next
bind = $mainMod, up, exec, pypr layout_center prev2
bind = $mainMod, down, exec, pypr layout_center next2
```

You can completely ignore `next2` and `prev2` if you are allowing focus change (when the layout is enabled) in a single direction, eg:

```sh
bind = $mainMod, up, movefocus, u
bind = $mainMod, down, movefocus, d
```

> _Added in version 1.8.0_

# Command

- `layout_center [command]` where *[command]* can be:
  - toggle
  - next
  - prev
  - next2
  - prev2

# Configuration

## `margin` (optional)

default value is `60`

margin (in pixels) used when placing the center window, calculated from the border of the screen.

Example to make the main window be 100px far from the monitor's limits:
```toml
margin = 100
```

## `offset` (optional)

default value is `[0, 0]`

offset in pixels applied to the main window position

Example shift the main window 20px down:
```toml
offset = [0, 20]
```

## `next` (optional)

not set by default

When the *layout_center* isn't active and the *next* command is triggered, defines the hyprland dispatcher command to run.

`next2` is a similar option, used by the `next2` command, allowing to map "next" to both vertical and horizontal focus change.

Eg:
```toml
next = "movefocus r"
```

## `prev` and `prev2` (optional)

Same as `next` but for the `prev` and `prev2` commands.


## `captive_focus` (optional)

default value is `false`

```toml
captive_focus = true
```

Sets the focus on the main window when the focus changes.
You may love it or hate it...
