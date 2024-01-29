![rect](https://github.com/hyprland-community/pyprland/assets/238622/3fab93b6-6445-4e7b-b757-035095b5c8e8)

## A plugin system for Hyprland

Host process for multiple Hyprland plugins,
aiming at simplicity and efficiency.

You can implement anything you can imagine using Python with [Hyprland API](https://wiki.hyprland.org/Configuring/Dispatchers/) and [events](https://wiki.hyprland.org/Plugins/Development/Event-list/)!

It has a safe design which is friendly for developers.

### → [Features/plugin list](https://github.com/hyprland-community/pyprland/wiki/Plugins)

### → [Getting started](https://github.com/hyprland-community/pyprland/wiki/Getting-started)

### → [Changes log](https://github.com/hyprland-community/pyprland/releases)

### →[The Wiki](https://github.com/hyprland-community/pyprland/wiki)

## Dependencies

- Hyprland >= 0.25
- Python >= 3.11

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=fdev31/pyprland&type=Date)](https://star-history.com/#fdev31/pyprland&Date)

## Latest major changes

### Git (future 1.8.0)

- `toggle_minimized` command renamed to `toggle_special` and moved to a separate plugin for clarity
  - add the [toggle_special](https://github.com/hyprland-community/pyprland/wiki/toggle_special) plugin to your config and rename the command in your `hyprland.conf` & scripts!
  - was provided by [expose](https://github.com/hyprland-community/pyprland/wiki/expose)
- New [layout_center](https://github.com/hyprland-community/pyprland/wiki/layout_center) plugin

### Wiki

- `Plugins` have been split, one page each

### 1.7.0

- **BREAKING CHANGE** [layout_center](https://github.com/hyprland-community/pyprland/wiki/monitors) plugin uses now a new syntax - full rewrite (expect a behavior change)
