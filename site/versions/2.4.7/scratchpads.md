---
commands:
  - name: toggle [scratchpad name]
    description: Toggle the given scratchpad
  - name: show [scratchpad name]
    description: Show the given scratchpad
  - name: hide [scratchpad name]
    description: Hide the given scratchpad
  - name: attach
    description: Toggle attaching/anchoring the currently focused window to the (last used) scratchpad

Note: show and hide can accept '*' as a parameter, applying changes to every scratchpad.

---
# scratchpads

Easily toggle the visibility of applications you use the most.

Configurable and flexible, while supporting complex setups it's easy to get started with:

```toml
[scratchpads.name]
command = "command to run"
class = "the window's class"  # check: hyprctl clients | grep class
size = "[width] [height]"  # size of the window relative to the screen size
```

<details>
<summary>Example</summary>

As an example, defining two scratchpads:

- _term_ which would be a kitty terminal on upper part of the screen
- _volume_ which would be a pavucontrol window on the right part of the screen


```toml
[scratchpads.term]
animation = "fromTop"
command = "kitty --class kitty-dropterm"
class = "kitty-dropterm"
size = "75% 60%"
max_size = "1920px 100%"
margin = 50

[scratchpads.volume]
animation = "fromRight"
command = "pavucontrol"
class = "org.pulseaudio.pavucontrol"
size = "40% 90%"
unfocus = "hide"
lazy = true
```

Shortcuts are generally needed:

```ini
bind = $mainMod,V,exec,pypr toggle volume
bind = $mainMod,A,exec,pypr toggle term
bind = $mainMod,Y,exec,pypr attach
```
</details>

- If you wish to have a more generic space for any application you may run, check [toggle_special](./toggle_special).
- When you create a scratchpad called "name", it will be hidden in `special:scratch_<name>`.
- Providing `class` allows a glitch free experience, mostly noticeable when using animations


## Commands

<CommandList :commands="$frontmatter.commands" />

> [!tip]
> You can use `"*"` as a _scratchpad name_ to target every scratchpad when using `show` or `hide`.
> You'll need to quote or escape the `*` character to avoid interpretation from your shell.

## Configuration

### `command` (REQUIRED)

This is the command you wish to run in the scratchpad.

It supports [Variables](./Variables)

### `animation`

Type of animation to use, default value is "fromTop":

- `null` / `""` (no animation)
- `fromTop` (stays close to upper screen border)
- `fromBottom` (stays close to lower screen border)
- `fromLeft` (stays close to left screen border)
- `fromRight` (stays close to right screen border)

### `size` (recommended)

No default value.

Each time scratchpad is shown, window will be resized according to the provided values.

For example on monitor of size `800x600` and `size= "80% 80%"` in config scratchpad always have size `640x480`,
regardless of which monitor it was first launched on.

> #### Format
>
> String with "x y" (or "width height") values using some units suffix:
>
> - **percents** relative to the focused screen size (`%` suffix), eg: `60% 30%`
> - **pixels** for absolute values (`px` suffix), eg: `800px 600px`
> - a mix is possible, eg: `800px 40%`

### `class` (recommended)

No default value.

Allows _Pyprland_ prepare the window for a correct animation and initial positioning.

### `position`

No default value, overrides the automatic margin-based position.

Sets the scratchpad client window position relative to the top-left corner.

Same format as `size` (see above)

Example of scratchpad that always seat on the top-right corner of the screen:

```toml
[scratchpads.term_quake]
command = "wezterm start --class term_quake"
position = "50% 0%"
size = "50% 50%"
class = "term_quake"
```

> [!note]
> If `position` is not provided, the window is placed according to `margin` on one axis and centered on the other.

### `multi`

Defaults to `true`.

When set to `false`, only one client window is supported for this scratchpad.
Otherwise other matching windows will be **attach**ed to the scratchpad.

## Advanced configuration

To go beyond the basic setup and have a look at every configuration item, you can read the following pages:

- [Advanced](./scratchpads_advanced) contains options for fine-tuners or specific tastes (eg: i3 compatibility)
- [Non-Standard](./scratchpads_nonstandard) contains options for "broken" applications
like progressive web apps (PWA) or emacsclient, use only if you can't get it to work otherwise

## Monitor specific overrides

You can use different settings for a specific screen.
Most attributes related to the display can be changed (not `command`, `class` or `process_tracking` for instance).

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
