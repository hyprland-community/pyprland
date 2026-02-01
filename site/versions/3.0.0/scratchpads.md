---
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

<PluginCommands plugin="scratchpads" />

> [!tip]
> You can use `"*"` as a _scratchpad name_ to target every scratchpad when using `show` or `hide`.
> You'll need to quote or escape the `*` character to avoid interpretation from your shell.

## Configuration

<PluginConfig plugin="scratchpads" linkPrefix="config-" :filter="['command', 'class', 'animation', 'size', 'position', 'margin', 'max_size', 'multi', 'lazy']" />

> [!tip]
> Looking for more options? See:
> - [Advanced Configuration](./scratchpads_advanced) - unfocus, excludes, monitor overrides, and more
> - [Troubleshooting](./scratchpads_nonstandard) - PWAs, emacsclient, custom window matching

### `command` <ConfigBadges plugin="scratchpads" option="command" /> {#config-command}

This is the command you wish to run in the scratchpad. It supports [variables](./Variables).

### `class` <ConfigBadges plugin="scratchpads" option="class" /> {#config-class}

Allows _Pyprland_ prepare the window for a correct animation and initial positioning.
Check your window's class with: `hyprctl clients | grep class`

### `animation` <ConfigBadges plugin="scratchpads" option="animation" /> {#config-animation}

Type of animation to use:

- `null` / `""` (no animation)
- `fromTop` (stays close to upper screen border)
- `fromBottom` (stays close to lower screen border)
- `fromLeft` (stays close to left screen border)
- `fromRight` (stays close to right screen border)

### `size` <ConfigBadges plugin="scratchpads" option="size" /> {#config-size}

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

### `position` <ConfigBadges plugin="scratchpads" option="position" /> {#config-position}

Overrides the automatic margin-based position.
Sets the scratchpad client window position relative to the top-left corner.

Same format as `size` (see above)

Example of scratchpad that always sits on the top-right corner of the screen:

```toml
[scratchpads.term_quake]
command = "wezterm start --class term_quake"
position = "50% 0%"
size = "50% 50%"
class = "term_quake"
```

> [!note]
> If `position` is not provided, the window is placed according to `margin` on one axis and centered on the other.

### `margin` <ConfigBadges plugin="scratchpads" option="margin" /> {#config-margin}

Pixels from the screen edge when using animations. Used to position the window along the animation axis.

### `max_size` <ConfigBadges plugin="scratchpads" option="max_size" /> {#config-max-size}

Maximum window size. Same format as `size`. Useful to prevent scratchpads from growing too large on big monitors.

### `multi` <ConfigBadges plugin="scratchpads" option="multi" /> {#config-multi}

When set to `false`, only one client window is supported for this scratchpad.
Otherwise other matching windows will be **attach**ed to the scratchpad.
Allows the `attach` command on the scratchpad.

### `lazy` <ConfigBadges plugin="scratchpads" option="lazy" /> {#config-lazy}

When `true`, the scratchpad command is only started on first use instead of at startup.

## Advanced configuration

To go beyond the basic setup and have a look at every configuration item, you can read the following pages:

- [Advanced](./scratchpads_advanced) contains options for fine-tuners or specific tastes (eg: i3 compatibility)
- [Non-Standard](./scratchpads_nonstandard) contains options for "broken" applications
like progressive web apps (PWA) or emacsclient, use only if you can't get it to work otherwise
