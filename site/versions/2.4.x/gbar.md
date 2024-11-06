---
commands:
  - name: gbar restart
    description: Restart/refresh gBar on the "best" monitor.
---

# gbar

Runs [gBar](https://github.com/scorpion-26/gBar) on the "best" monitor from a list of monitors.

- Will take care of starting gbar on startup (you must not run it from another source like `hyprland.conf`).
- Automatically restarts gbar on crash
- Checks which monitors are on and take the best one from a provided list

## Command

<CommandList :commands="$frontmatter.commands" />


## Configuration


### `monitors` (REQUIRED)

List of monitors to chose from, the first have higher priority over the second one etc...


## Example

```sh
[gbar]
monitors = ["DP-1", "HDMI-1", "HDMI-1-A"]
```
