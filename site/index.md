---
# https://vitepress.dev/reference/default-theme-home-page
layout: home

hero:
  text: "Extensions for your desktop environment"
  tagline: Enhance your desktop experience with Pyprland
  image:
    src: /logo.svg
    alt: logo
  actions:
    - theme: brand
      text: Getting started
      link: ./Getting-started
    - theme: alt
      text: Plugins
      link: ./Plugins
    - theme: alt
      text: Report something
      link: https://github.com/hyprland-community/pyprland/issues/new/choose

features:
  - title: TOML format
    details: Simple and flexible configuration file(s)
  - title: Customizable
    details: Create your own Hyprland experience
  - title: Fast and easy
    details: Designed for performance and simplicity
---

# What is Pyprland?

It's a software that extends the functionality of your desktop environment (Hyprland, Niri, etc...), adding new features and improving the existing ones.

It also enables a high degree of customization and automation, making it easier to adapt to your workflow.

To understand the potential of Pyprland, you can check the [plugins](./Plugins) page.

# Major recent changes

- The [Scratchpads](/monitors) got reworked to better satisfy current Hyprland version
- New [Stash](/stash) plugin, allowing to park windows and show/hide them easily
- Self documented using cli "doc" command
- Schema validation and "always in sync" configurations and commands (doc and code)
- Major rewrite of the [Monitors plugin](/monitors) delivers improved stability and functionality.
- The [Wallpapers plugin](/wallpapers) now applies [rounded corners](/wallpapers#radius) per display and derives cohesive [color schemes from the background](/wallpapers#templates) (Matugen/Pywal-inspired).

