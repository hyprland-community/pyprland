![rect](https://github.com/hyprland-community/pyprland/assets/238622/3fab93b6-6445-4e7b-b757-035095b5c8e8)

[![Hyprland](https://img.shields.io/badge/Made%20for-Hyprland-blue)](https://github.com/hyprwm/Hyprland)
[![Discord](https://img.shields.io/discord/1055990214411169892?label=discord)](https://discord.com/channels/1055990214411169892/1230972154330218526)

[Documentation](https://github.com/hyprland-community/pyprland/wiki) • [Discussions](https://github.com/hyprland-community/pyprland/discussions) • [Changes History](https://github.com/hyprland-community/pyprland/releases) • [Share Your Setup](https://github.com/hyprland-community/pyprland/discussions/46)


## Enhance your Hyprland experience with Pyprland

Welcome to Pyprland, your gateway to extending the capabilities of [Hyprland](https://hyprland.org/). Pyprland offers a plethora of plugins designed for simplicity and efficiency, allowing you to supercharge your productivity and customize your user experience.

You can think of it as a *Gnome tweak tool* but for Hyprland users (involves editing text files). With a "100%" plugin-based architecture, Pyprland is designed to be lightweight and easy to use.
Note that usage of Python and architecture of the software encourages using many plugins with little impact on the footprint and performance.

Contributions, bug reports and comments are welcome.

- Explore our variety of [plugins](https://github.com/hyprland-community/pyprland/wiki/Plugins) to tailor your Hyprland setup to your liking.
- New users, check the [getting started](https://github.com/hyprland-community/pyprland/wiki/Getting-started) guide.


<details>
<summary>
About Pyprland
</summary>

[![Packaging Status](https://repology.org/badge/vertical-allrepos/pyprland.svg)](https://repology.org/project/pyprland/versions)

🎉 Hear what others are saying:
- ["It just works very very well" - The Linux Cast (video)](https://youtu.be/Cjn0SFyyucY?si=hGb0TM9IDvlbcD6A&t=131) - February 2024
- [You NEED This in your Hyprland Config - LibrePhoenix (video)](https://www.youtube.com/watch?v=CwGlm-rpok4) - October 2023 (*Now [TOML](https://toml.io/en/) format is preferred over [JSON](https://www.w3schools.com/js/js_json_intro.asp))
</details>

<details>

<summary>
Contributing
</summary>

Check out the [creating a pull request](https://docs.github.com/fr/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request) document for guidance.

- Report bugs or propose features [here](https://github.com/hyprland-community/pyprland/issues)
- Improve our [wiki](https://github.com/hyprland-community/pyprland/wiki)

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
    - **aiofiles**
</details>

<details>
<summary>
Latest major changes
</summary>

Check the [Releases change log](https://github.com/hyprland-community/pyprland/releases) for more information

### 2.2

- Added [wallpapers](https://github.com/hyprland-community/pyprland/wiki/wallpapers) and [system_notifier](https://github.com/hyprland-community/pyprland/wiki/system_notifier) plugins.
- Deprecated [class_match](https://github.com/hyprland-community/pyprland/wiki/scratchpads_nonstandard) in [scratchpads](https://github.com/hyprland-community/pyprland/wiki/scratchpads)
- Added [gbar](https://github.com/hyprland-community/pyprland/wiki/gbar) in 2.2.6
- [scratchpads](https://github.com/hyprland-community/pyprland/wiki/scratchpads) supports multiple client windows (in 2.2.11 and 2.2.13)
- [Monitors](https://github.com/hyprland-community/pyprland/wiki/monitors) and [scratchpads](https://github.com/hyprland-community/pyprland/wiki/scratchpads) supports rotation in 2.2.13
- Improve [Nix support](https://github.com/hyprland-community/pyprland/wiki/Nix)


### 2.1

- Requires Hyprland >= 0.37
- [Monitors](https://github.com/hyprland-community/pyprland/wiki/monitors) plugin improvements.

### 2.0

- New dependency: [aiofiles](https://pypi.org/project/aiofiles/)
- Added [hysteresis](https://github.com/hyprland-community/pyprland/wiki/scratchpads#hysteresis-optional) support for [scratchpads](https://github.com/hyprland-community/pyprland/wiki/scratchpads).

### 1.10

- New [fetch_client_menu](https://github.com/hyprland-community/pyprland/wiki/fetch_client_menu) and [shortcuts_menu](https://github.com/hyprland-community/pyprland/wiki/shortcuts_menu) plugins.

### 1.9

- Introduced [shortcuts_menu](https://github.com/hyprland-community/pyprland/wiki/shortcuts_menu) plugin.

### 1.8

- Requires Hyprland >= 0.30
- Added [layout_center](https://github.com/hyprland-community/pyprland/wiki/layout_center) plugin.

</details>

<a href="https://star-history.com/#fdev31/pyprland&Date">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=fdev31/pyprland&type=Timeline&theme=dark" />
    <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=fdev31/pyprland&type=Timeline" />
    <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=fdev31/pyprland&type=Timeline" />
  </picture>
</a>
