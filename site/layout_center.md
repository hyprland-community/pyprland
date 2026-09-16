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

using the following in `hyprland.lua`:
```lua
bind = $mainMod, M, exec, pypr layout_center toggle # toggle the layout
hl.bind(mainMod .. " + M", hl.dsp.exec_cmd(pypr .. " layout_center toggle"))
--focus change keys
hl.bind(mainMod .. " + left", hl.dsp.exec_cmd(pypr .. " layout_center prev"))
hl.bind(mainMod .. " + right", hl.dsp.exec_cmd(pypr .. " layout_center next"))
hl.bind(mainMod .. " + up", hl.dsp.exec_cmd(pypr .. " layout_center prev2"))
hl.bind(mainMod .. " + up", hl.dsp.exec_cmd(pypr .. " layout_center next2"))
```

You can completely ignore `next2` and `prev2` if you are allowing focus change in a single direction (when the layout is enabled), eg:

```lua
hl.bind(mainMod .. " + up", hl.dsp.focus({ direction = "up" }))
hl.bind(mainMod .. " + down", hl.dsp.focus({ direction = "down" }))
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

<ConfigChoices plugin="layout_center" option="on_new_client" />

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
