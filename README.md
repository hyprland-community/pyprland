# Pyprland

## Tweaks & extensions for Hyprland

Host process for multiple Hyprland plugins, such as:

- scratchpads (aka "dropdowns")
- multi-monitor friendly behavior (placement, focus, ...)
- shortcut / togglers for hyprctl commands
- miscelaneous obscure commands for specific usages
- temporary workarounds
- anything you can imagine using [Hyprland API](https://wiki.hyprland.org/Configuring/Dispatchers/) and [events](https://wiki.hyprland.org/Plugins/Development/Event-list/)!

Check the [Getting started](https://github.com/hyprland-community/pyprland/wiki/Getting-started) page and the [plugins list](https://github.com/hyprland-community/pyprland/wiki/Plugins), finally browse the [wiki](https://github.com/hyprland-community/pyprland/wiki) for more information.

# Changelog

> [!note]
>  **WIP: current `main` branch**
> 
> - nothing yet

# 1.5.2

- commands can now use "-" instead of "_", eg: `pypr change-workspace +1`
- `monitors`: `unknown` command isn't blocking pypr anymore
- fix package's required Python version

## 1.5.1

- scratchpads stability improvements:
    - review plugin processing logic, making code safer
    - Using hyprland's notifications in case of serious errors
    - rework focus handling logic to handle more corner cases
- improved `pypr -h` readability

## 1.5.0

- Add support for a [TOML](https://toml.io/) configuration file, will be used if found (instead of JSON)
  - JSON format will probably stay supported but is more prone to errors
- Wiki uses TOML as a reference

## 1.4.5

- fix some regression using `size` & `position` in scratchpads
- improve logging of client connexion errors

## 1.4.4

- add an [excludes](https://github.com/hyprland-community/pyprland/wiki/Plugins#excludes-optional) option to scratchpads
- fix random problem showing scratches

## 1.4.3

- more resilient to slowly starting scratchpads

## 1.4.2

- [two new options](https://github.com/hyprland-community/pyprland/wiki/Plugins#size-optional) for scratchpads: `position` and `size` - from @iliayar
- simplification of the scratchpad code - fixes misc issues
- bugfixes

## 1.4.1

- minor bugfixes

## 1.4.0

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

