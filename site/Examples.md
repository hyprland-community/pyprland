# Examples

This page provides complete configuration examples to help you get started.

## Basic Setup

A minimal configuration with a few popular plugins:

### pyprland.toml

```toml
[pyprland]
plugins = [
    "scratchpads",
    "magnify",
    "expose",
]

[scratchpads.term]
command = "kitty --class kitty-dropterm"
class = "kitty-dropterm"
size = "75% 60%"
animation = "fromTop"

[scratchpads.volume]
command = "pavucontrol"
class = "org.pulseaudio.pavucontrol"
size = "40% 90%"
animation = "fromRight"
lazy = true
```

### hyprland.conf

```ini
$pypr = /usr/bin/pypr

bind = $mainMod, A, exec, $pypr toggle term
bind = $mainMod, V, exec, $pypr toggle volume
bind = $mainMod, B, exec, $pypr expose
bind = $mainMod SHIFT, Z, exec, $pypr zoom
```

## Full-Featured Setup

A comprehensive configuration demonstrating multiple plugins and features:

### pyprland.toml

```toml
[pyprland]
plugins = [
  "scratchpads",
  "lost_windows",
  "monitors",
  "toggle_dpms",
  "magnify",
  "expose",
  "shift_monitors",
  "workspaces_follow_focus",
]

[monitors.placement]
"Acer".top_center_of = "Sony"

[workspaces_follow_focus]
max_workspaces = 9

[expose]
include_special = false

[scratchpads.stb]
animation = "fromBottom"
command = "kitty --class kitty-stb sstb"
class = "kitty-stb"
lazy = true
size = "75% 45%"

[scratchpads.stb-logs]
animation = "fromTop"
command = "kitty --class kitty-stb-logs stbLog"
class = "kitty-stb-logs"
lazy = true
size = "75% 40%"

[scratchpads.term]
animation = "fromTop"
command = "kitty --class kitty-dropterm"
class = "kitty-dropterm"
size = "75% 60%"

[scratchpads.volume]
animation = "fromRight"
command = "pavucontrol"
class = "org.pulseaudio.pavucontrol"
lazy = true
size = "40% 90%"
unfocus = "hide"
```

### hyprland.conf

```ini
# Use pypr-client for faster response in key bindings
$pypr = uwsm-app -- /usr/local/bin/pypr-client

bind = $mainMod SHIFT,  Z, exec, $pypr zoom
bind = $mainMod ALT,    P, exec, $pypr toggle_dpms
bind = $mainMod SHIFT,  O, exec, $pypr shift_monitors +1
bind = $mainMod,        B, exec, $pypr expose
bind = $mainMod,        K, exec, $pypr change_workspace +1
bind = $mainMod,        J, exec, $pypr change_workspace -1
bind = $mainMod,        L, exec, $pypr toggle_dpms
bind = $mainMod  SHIFT, M, exec, $pypr toggle stb stb-logs
bind = $mainMod,        A, exec, $pypr toggle term
bind = $mainMod,        V, exec, $pypr toggle volume
```

> [!note]
> This example uses `pypr-client` for faster key binding response. See [Commands: pypr-client](./Commands#pypr-client) for details.

## Advanced Features

### Variables

You can define reusable variables in your configuration to avoid repetition and make it easier to switch terminals or other tools.

Define variables in the `[pyprland.variables]` section:

```toml
[pyprland.variables]
term = "foot"
term_classed = "foot -a"  # For kitty, use "kitty --class"
```

Then use them in plugin configurations that support variable substitution:

```toml
[scratchpads.term]
command = "[term_classed] scratchterm"
class = "scratchterm"
```

This way, switching from `foot` to `kitty` only requires changing the variables, not every scratchpad definition.

See [Variables](./Variables) for more details.

### Text Filters

Some plugins support text filters for transforming output. Filters use a syntax similar to sed's `s` command:

```toml
filter = 's/foo/bar/'           # Replace first "foo" with "bar"
filter = 's/foo/bar/g'          # Replace all occurrences
filter = 's/.*started (.*)/\1 has started/'  # Regex with capture groups
filter = 's#</?div>##g'         # Use different delimiter
```

See [Filters](./filters) for more details.

## Community Examples

Browse community-contributed configuration files:

- [GitHub examples folder](https://github.com/hyprland-community/pyprland/tree/main/examples)

Feel free to share your own configurations by contributing to the repository.

## Tips

- [Optimizations](./Optimizations) - Performance tuning tips
- [Troubleshooting](./Troubleshooting) - Common issues and solutions
- [Multiple Configuration Files](./MultipleConfigurationFiles) - Split your config for better organization
