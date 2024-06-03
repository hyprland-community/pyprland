# gbar

Runs [gBar](https://github.com/scorpion-26/gBar) on the "best" monitor from a list of monitors.

Will take care of starting gbar on startup (you must not run it from another source like `hyprland.conf`).

> _Added in 2.2.6_

## Commands

- `gbar restart` - Restart/refresh gBar on the "best" monitor.

## Configuration


### `monitors`

List of monitors to chose from, the first have higher priority over the second one etc...


## Example

```sh
[gbar]
monitors = ["DP-1", "HDMI-1", "HDMI-1-A"]
```
