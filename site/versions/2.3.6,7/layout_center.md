---
commands:
  - name: layout_center toggle
    description: toggles the layout on and off
  - name: layout_center next
    description: switches to the next window (if layout is on) else runs the `next` command
  - name: layout_center prev
    description: switches to the previous window (if layout is on) else runs the `prev` command
  - name: layout_center next2
    description: switches to the next window (if layout is on) else runs the `next2` command
  - name: layout_center prev2
    description: switches to the previous window (if layout is on) else runs the `prev2` command

---
# layout_center

Implements a workspace layout where one window is bigger and centered,
other windows are tiled as usual in the background.

On `toggle`, the active window is made floating and centered if the layout wasn't enabled, else reverts the floating status.

With `next` and `prev` you can cycle the active window, keeping the same layout type.
If the layout_center isn't active and `next` or `prev` is used, it will call the "next" and "prev" configuration options.

To allow full override of the focus keys, `next2` and `prev2` are provided, they do the same actions as "next" and "prev" but allow different fallback commands.

<details>
<summary>Configuration sample</summary>

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
## focus change keys
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

</details>


## Commands

<CommandList :commands="$frontmatter.commands" />

## Configuration

### `on_new_client` (optional)

Defaults to `"foreground"`.

Changes the behavior when a new window opens, possible options are:

- "foreground" to make the new window the main window
- "background" to make the new window appear in the background
- "close" to stop the centered layout when a new window opens

### `style` (optional)

| Requires Hyprland > 0.40.0

Not set by default.

Allow to set a list of styles to the main (centered) window, eg:

```toml
style = ["opacity 1", "bordercolor rgb(FFFF00)"]
```

### `margin` (optional)

default value is `60`

margin (in pixels) used when placing the center window, calculated from the border of the screen.

Example to make the main window be 100px far from the monitor's limits:
```toml
margin = 100
```

You can also set a different margin for width and height by using a list:
```toml
margin = [10, 60]
```

### `offset` (optional)

default value is `[0, 0]`

offset in pixels applied to the main window position

Example shift the main window 20px down:
```toml
offset = [0, 20]
```

### `next` (optional)

not set by default

When the *layout_center* isn't active and the *next* command is triggered, defines the hyprland dispatcher command to run.

`next2` is a similar option, used by the `next2` command, allowing to map "next" to both vertical and horizontal focus change.

Eg:
```toml
next = "movefocus r"
```

### `prev` and `prev2` (optional)

Same as `next` but for the `prev` and `prev2` commands.


### `captive_focus` (optional)

default value is `false`

```toml
captive_focus = true
```

Sets the focus on the main window when the focus changes.
You may love it or hate it...
