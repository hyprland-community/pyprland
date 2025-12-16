![rect](https://github.com/hyprland-community/pyprland/assets/238622/3fab93b6-6445-4e7b-b757-035095b5c8e8)

[![Hyprland](https://img.shields.io/badge/Made%20for-Hyprland-blue)](https://github.com/hyprwm/Hyprland)
[![Discord](https://img.shields.io/discord/1055990214411169892?label=discord)](https://discord.com/channels/1055990214411169892/1230972154330218526)

[Documentation](https://hyprland-community.github.io/pyprland) • [Discussions](https://github.com/hyprland-community/pyprland/discussions) • [Changes History](https://github.com/hyprland-community/pyprland/releases) • [Share Your Setup](https://github.com/hyprland-community/pyprland/discussions/46)

## Enhance your Hyprland experience with Pyprland

Welcome to Pyprland, your gateway to extending the capabilities of [Hyprland](https://hyprland.org/).
Pyprland offers a plethora of plugins designed for simplicity and efficiency,
allowing you to supercharge your productivity and customize your user experience.

You can think of it as a *Gnome tweak tool* but for Hyprland users (involves editing text files).
With a "100%" plugin-based architecture, Pyprland is designed to be lightweight and easy to use.

Note that usage of Python and architecture of the software encourages using many plugins
with little impact on the footprint and performance.

Contributions, suggestions, bug reports and comments are welcome.

- Explore our variety of [plugins](https://hyprland-community.github.io/pyprland/Plugins.html)
  to tailor your Hyprland setup to your liking.
- New users, check the [getting started](https://hyprland-community.github.io/pyprland/Getting-started.html) guide.

<details>
<summary>
About Pyprland (latest stable is: <b>2.4.3</b>)
</summary>

You may also want to visit [my dotfiles](https://github.com/fdev31/dotfiles) for some working examples.

[![Packaging Status](https://repology.org/badge/vertical-allrepos/pyprland.svg)](https://repology.org/project/pyprland/versions)

🎉 Hear what others are saying:

- [Elsa in Mac](https://elsainmac.tistory.com/915) some tutorial article for fedora in Korean with a nice short demo video
- [Archlinux Hyprland dotfiles](https://github.com/DinDotDout/.dotfiles/blob/main/conf-hyprland/.config/hypr/pyprland.toml) + [video](https://www.youtube.com/watch?v=jHuzcjf-FGM)
- ["It just works very very well" - The Linux Cast (video)](https://youtu.be/Cjn0SFyyucY?si=hGb0TM9IDvlbcD6A&t=131) - February 2024
- [You NEED This in your Hyprland Config - LibrePhoenix (video)](https://www.youtube.com/watch?v=CwGlm-rpok4) - October 2023 (*Now [TOML](https://toml.io/en/) format is preferred over [JSON](https://www.w3schools.com/js/js_json_intro.asp))

</details>

<details>

<summary>
Contributing
</summary>

Check out the [creating a pull request](https://docs.github.com/fr/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request) document for guidance.

- Report bugs or propose features [here](https://github.com/hyprland-community/pyprland/issues)
- Improve our [wiki](https://hyprland-community.github.io/pyprland/)
- Read the [internal ticket list](https://github.com/hyprland-community/pyprland/blob/main/tickets.rst) for some PR ideas

and if you have coding skills you can also

- Enhance the coverage of our [tests](https://github.com/hyprland-community/pyprland/tree/main/tests)
- Propose & write new plugins or enhancements

</details>

<details>
<summary>
Dependencies
</summary>

- **Hyprland** >= 0.37
- **Python** >= 3.11
    - **aiofiles** (optional but recommended)
</details>

<details>
<summary>
Latest major changes
</summary>

Check the [Releases change log](https://github.com/hyprland-community/pyprland/releases) for more information

### 2.4

- Scratchpads are now pinned by default (set `pinned = false` for the old behavior)
- Version >=2.4.4 is required for Hyprland 0.48.0
- A snappier `pypr-client` command is available, meant to be used in the keyboard bindings (NOT to start pypr on startup!), eg:
```sh
$pypr = uwsm-app -- pypr-client
bind = $mainMod SHIFT, Z, exec, $pypr zoom ++0.5
 ```

### 2.3

- Supports *Hyprland > 0.40.0*
- Improved code kwaleetee
- [monitors](https://hyprland-community.github.io/pyprland/monitors) allows general monitor settings
- [scratchpads](https://hyprland-community.github.io/pyprland/scratchpads)
  - better multi-window support
  - better `preserve_aspect` implementation (i3 "compatibility")

### 2.2

- Added [wallpapers](https://hyprland-community.github.io/pyprland/wallpapers) and [system_notifier](https://hyprland-community.github.io/pyprland/system_notifier) plugins.
- Deprecated [class_match](https://hyprland-community.github.io/pyprland/scratchpads_nonstandard) in [scratchpads](https://hyprland-community.github.io/pyprland/scratchpads)
- Added [gbar](https://hyprland-community.github.io/pyprland/gbar) in 2.2.6
- [scratchpads](https://hyprland-community.github.io/pyprland/scratchpads) supports multiple client windows (using 2.2.19 is recommended)
- [monitors](https://hyprland-community.github.io/pyprland/monitors) and [scratchpads](https://hyprland-community.github.io/pyprland/scratchpads) supports rotation in 2.2.13
- Improve [Nix support](https://hyprland-community.github.io/pyprland/Nix)

### 2.1

- Requires Hyprland >= 0.37
- [Monitors](https://hyprland-community.github.io/pyprland/monitors) plugin improvements.

### 2.0

- New dependency: [aiofiles](https://pypi.org/project/aiofiles/)
- Added [hysteresis](https://hyprland-community.github.io/pyprland/scratchpads#hysteresis-optional) support for [scratchpads](https://hyprland-community.github.io/pyprland/scratchpads).

### 1.10

- New [fetch_client_menu](https://hyprland-community.github.io/pyprland/fetch_client_menu) and [shortcuts_menu](https://hyprland-community.github.io/pyprland/shortcuts_menu) plugins.

### 1.9

- Introduced [shortcuts_menu](https://hyprland-community.github.io/pyprland/shortcuts_menu) plugin.

### 1.8

- Requires Hyprland >= 0.30
- Added [layout_center](https://hyprland-community.github.io/pyprland/layout_center) plugin.

</details>

<a href="https://star-history.com/#fdev31/pyprland&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=fdev31/pyprland&type=Timeline&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=fdev31/pyprland&type=Timeline" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=fdev31/pyprland&type=Timeline" />
  </picture>
</a>
