---
---
# layout_center

Implements a workspace layout where one window is bigger and centered,
other windows are tiled as usual in the background.

On `toggle`, the active window is made floating and centered if the layout wasn't enabled, else reverts the floating status.

With `next` and `prev` you can cycle the active window, keeping the same layout type.
If the layout_center isn't active and `next` or `prev` is used, it will call the [next](#config-next) and [prev](#config-next) configuration options.

To allow full override of the focus keys, `next2` and `prev2` are provided, they do the same actions as `next` and `prev` but allow different fallback commands.

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

You can completely ignore `next2` and `prev2` if you are allowing focus change in a single direction (when the layout is enabled), eg:

```sh
bind = $mainMod, up, movefocus, u
bind = $mainMod, down, movefocus, d
```

</details>


## Commands

<PluginCommands plugin="layout_center" />

## Configuration

<PluginConfig plugin="layout_center" linkPrefix="config-" />

### `style` <ConfigBadges plugin="layout_center" option="style" /> {#config-style}

Custom Hyprland style rules applied to the centered window. Requires Hyprland > 0.40.0.

```toml
style = ["opacity 1", "bordercolor rgb(FFFF00)"]
```

### `on_new_client` <ConfigBadges plugin="layout_center" option="on_new_client" /> {#config-on-new-client}

Behavior when a new window opens while layout is active:

- `"focus"` (or `"foreground"`) - make the new window the main window
- `"background"` - make the new window appear in the background  
- `"close"` - stop the centered layout when a new window opens

### `next` / `prev` <ConfigBadges plugin="layout_center" option="next" /> {#config-next}

Hyprland dispatcher command to run when layout_center isn't active:

```toml
next = "movefocus r"
prev = "movefocus l"
```

### `next2` / `prev2` <ConfigBadges plugin="layout_center" option="next2" /> {#config-next2}

Alternative fallback commands for vertical navigation:

```toml
next2 = "movefocus d"
prev2 = "movefocus u"
```

### `offset` <ConfigBadges plugin="layout_center" option="offset" /> {#config-offset}

offset in pixels applied to the main window position

Example shift the main window 20px down:
```toml
offset = [0, 20]
```


### `margin` <ConfigBadges plugin="layout_center" option="margin" /> {#config-margin}

margin (in pixels) used when placing the center window, calculated from the border of the screen.

Example to make the main window be 100px far from the monitor's limits:
```toml
margin = 100
```
You can also set a different margin for width and height by using a list:

```toml
margin = [100, 100]
```
