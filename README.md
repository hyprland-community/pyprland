# Pyprland

## Scratchpads, smart monitor placement and other tweaks for hyprland

Host process for multiple Hyprland plugins.

Check the [wiki](https://github.com/hyprland-community/pyprland/wiki) for more information.

# 1.4.2 (WIP)

- [two new options](https://github.com/hyprland-community/pyprland/wiki/Plugins#size-optional) for scratchpads: `position` and `size` - from @iliayar
- bugfixes

# 1.4.1

- minor bugfixes

# 1.4.0

- Add [expose](https://github.com/hyprland-community/pyprland/wiki/Plugins#expose) addon
- scratchpad: add [lazy](https://github.com/hyprland-community/pyprland/wiki/Plugins#lazy-optional) option
- fix `scratchpads`'s position on monitors using scaling
- improve error handling & logging, enable debug logs with `--debug <filename>`

## 1.3.1

- `monitors` triggers rules on startup (not only when a monitor is plugged)

## 1.3.0

- Add `shift_monitors` addon
- Add `monitors` addon
- scratchpads: more reliable client tracking
- bugfixes

## 1.2.1

- scratchpads have their own special workspaces now
- misc improvements

## 1.2.0

- Add `magnify` addon
- focus fix when closing a scratchpad
- misc improvements

## 1.1.0

- Add `lost_windows` addon
- Add `toggle_dpms` addon
- `workspaces_follow_focus` now requires hyprland 0.25.0
- misc improvements

## 1.0.1, 1.0.2

- bugfixes & improvements

## 1.0

- First release, a modular hpr-scratcher (`scratchpads` plugin)
- Add `workspaces_follow_focus` addon

