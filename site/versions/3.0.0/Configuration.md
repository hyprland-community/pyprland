# Configuration

This page covers the configuration file format and available options.

## File Location

The default configuration file is:

```
~/.config/hypr/pyprland.toml
```

You can specify a different path using the `--config` flag:

```sh
pypr --config /path/to/config.toml
```

## Format

Pyprland uses the [TOML format](https://toml.io/). The basic structure is:

```toml
[pyprland]
plugins = ["plugin_name", "other_plugin"]

[plugin_name]
option = "value"

[plugin_name.nested_option]
suboption = 42
```

## [pyprland] Section

The main section configures the Pyprland daemon itself.

| Option | Description |
|--------|-------------|
| `plugins` · *list* · **required** | List of plugins to load |
| `include` · *list[Path]* | Additional config files or folders to include |
| `plugins_paths` · *list[Path]* | Additional paths to search for third-party plugins |
| `colored_handlers_log` · *bool* · =`true` | Enable colored log output for event handlers (debugging) |
| `notification_type` · *str* · =`"auto"` | Notification method: 'auto', 'notify-send', or 'native' |
| `variables` · *dict* | User-defined variables for string substitution (see Variables page) |
| `hyprland_version` · *str* | Override auto-detected Hyprland version (e.g., '0.40.0') |
| `desktop` · *str* | Override auto-detected desktop environment (e.g., 'hyprland', 'niri'). Empty means auto-detect. |


### `include` *list[Path]* {#config-include}

List of additional configuration files to include. See [Multiple Configuration Files](./MultipleConfigurationFiles) for details.

### `notification_type` *str* · =`"auto"` {#config-notification-type}

Controls how notifications are displayed:

| Value | Behavior |
|-------|----------|
| `"auto"` | Adapts to environment (Niri uses `notify-send`, Hyprland uses `hyprctl notify`) |
| `"notify-send"` | Forces use of `notify-send` command |
| `"native"` | Forces use of compositor's native notification system |

### `variables` *dict* {#config-variables}

Custom variables that can be used in plugin configurations. See [Variables](./Variables) for usage details.

## Examples

```toml
[pyprland]
plugins = [
    "scratchpads",
    "magnify",
    "expose",
]
notification_type = "notify-send"
```

### Plugin Configuration

Each plugin can have its own configuration section. The format depends on the plugin:

```toml
# Simple options
[magnify]
factor = 2

# Nested options (e.g., scratchpads)
[scratchpads.term]
command = "kitty --class kitty-dropterm"
class = "kitty-dropterm"
size = "75% 60%"
```

See individual [plugin documentation](./Plugins) for available options.

### Multiple Configuration Files

You can split your configuration across multiple files using `include`:

```toml
[pyprland]
include = [
    "~/.config/hypr/scratchpads.toml",
    "~/.config/hypr/monitors.toml",
]
plugins = ["scratchpads", "monitors"]
```

See [Multiple Configuration Files](./MultipleConfigurationFiles) for details.

## Hyprland Integration

Most plugins provide commands that you'll want to bind to keys. Add bindings to your `hyprland.conf`:

```ini
# Define pypr command (adjust path as needed)
$pypr = /usr/bin/pypr

# Example bindings
bind = $mainMod, A, exec, $pypr toggle term
bind = $mainMod, B, exec, $pypr expose
bind = $mainMod SHIFT, Z, exec, $pypr zoom
```

> [!tip]
> For faster key bindings, use `pypr-client` instead of `pypr`. See [Commands](./Commands#pypr-client) for details.

> [!tip]
> Command names can use dashes or underscores interchangeably.
> E.g., `pypr shift_monitors` and `pypr shift-monitors` are equivalent.

## Validation

You can validate your configuration without running the daemon:

```sh
pypr validate
```

This checks your config against plugin schemas and reports any errors.

## Tips

- See [Examples](./Examples) for complete configuration samples
- See [Optimizations](./Optimizations) for performance tips
- Only enable plugins you actually use in the `plugins` array
