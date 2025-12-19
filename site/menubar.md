---
commands:
  - name: bar restart
    description: Restart/refresh Menu Bar on the "best" monitor.
  - name: bar stop
    description: Stop the Menu Bar process
---

# menubar

Runs your favorite bar app (gbar, ags / hyprpanel, waybar, ...) with option to pass the "best" monitor from a list of monitors.

- Will take care of starting the command on startup (you must not run it from another source like `hyprland.conf`).
- Automatically restarts the menu bar on crash
- Checks which monitors are on and take the best one from a provided list

## Command

<CommandList :commands="$frontmatter.commands" />

## Configuration

### `command` (REQUIRED)

The command which runs the menu bar. The string `[monitor]` will be replaced by the best monitor.

### `monitors`

List of monitors to chose from, the first have higher priority over the second one etc...


## Example

```sh
[gbar]
monitors = ["DP-1", "HDMI-1", "HDMI-1-A"]
```
