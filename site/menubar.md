---
---

# menubar

Runs your favorite bar app (gbar, ags / hyprpanel, waybar, ...) with option to pass the "best" monitor from a list of monitors.

- Will take care of starting the command on startup (you must not run it from another source like `hyprland.conf`).
- Automatically restarts the menu bar on crash
- Checks which monitors are on and take the best one from a provided list

<details>
<summary>Example</summary>

```toml
[menubar]
command = "gBar bar [monitor]"
monitors = ["DP-1", "HDMI-1", "HDMI-1-A"]
```

</details>

> [!tip]
> This plugin supports both Hyprland and Niri. It will automatically detect the environment and use the appropriate IPC commands.

## Commands

<PluginCommands plugin="menubar" />

## Configuration

<PluginConfig plugin="menubar" linkPrefix="config-" />

### `command` {#config-command}

<ConfigDefault plugin="menubar" option="command" />

The command to run the bar. Use `[monitor]` as a placeholder for the monitor name:

```toml
command = "waybar -o [monitor]"
```
