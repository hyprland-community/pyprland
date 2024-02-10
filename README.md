![rect](https://github.com/hyprland-community/pyprland/assets/238622/3fab93b6-6445-4e7b-b757-035095b5c8e8)

## Extending Hyprland's features

Pyprland is a host process for multiple [Hyprland](https://hyprland.org/) extensions,
aiming at simplicity and efficiency.

It provides a variety of [plugins](https://github.com/hyprland-community/pyprland/wiki/Plugins) you can enable to your liking.

New users need to read the [getting started](https://github.com/hyprland-community/pyprland/wiki/Getting-started) page.

→ [Documentation](https://github.com/hyprland-community/pyprland/wiki)

→ [Changes log](https://github.com/hyprland-community/pyprland/releases)


→ [Discussions](https://github.com/hyprland-community/pyprland/discussions)

## Dependencies

- Hyprland >= 0.30 (versions < 1.8 can run on Hyprland 0.25)
- Python >= 3.11

## Latest major changes

### Git (future 1.10)

- New `fetch_client` plugin (shows a menu to bring a window to the active desktop)

### 1.9

- New [shortcuts_menu](https://github.com/hyprland-community/pyprland/wiki/shortcuts_menu) plugin

### 1.8

- `toggle_minimized` command renamed to `toggle_special` and moved to a separate plugin for clarity
  - add the [toggle_special](https://github.com/hyprland-community/pyprland/wiki/toggle_special) plugin to your config and rename the command in your `hyprland.conf` & scripts!
  - was provided by [expose](https://github.com/hyprland-community/pyprland/wiki/expose)
- [monitors](https://github.com/hyprland-community/pyprland/wiki/monitors) plugin improved a lot. If you were disappointed with a previous experience, give another chance to the latest `1.8` version.
- New [layout_center](https://github.com/hyprland-community/pyprland/wiki/layout_center) plugin

- Automated testing have improved a lot

### 1.7

- **BREAKING CHANGE** [monitors](https://github.com/hyprland-community/pyprland/wiki/monitors) plugin uses now a new syntax - full rewrite (expect a behavior change)

## Developers

If you feel like contributing, you are welcome. It can be done in many different ways:

- [bug reporting](https://github.com/hyprland-community/pyprland/issues) or proposing solid feature requests
- Improving the [wiki](https://github.com/hyprland-community/pyprland/wiki) (catching/fixing mistakes, helping with the formal structure, additional content, better wording, etc...)
- Writing [new plugins](https://github.com/hyprland-community/pyprland/wiki/Development)
- Improving existing [plugins](https://github.com/hyprland-community/pyprland/wiki/Plugins)
- Improving [test coverage](https://github.com/hyprland-community/pyprland/tree/main/tests)

Check the [creating a pull request](https://docs.github.com/fr/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request) document if you are not familiar with it

## Star History

<a href="https://star-history.com/#fdev31/pyprland&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=fdev31/pyprland&type=Timeline&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=fdev31/pyprland&type=Timeline" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=fdev31/pyprland&type=Timeline" />
  </picture>
</a>
