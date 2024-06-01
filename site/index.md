---
# https://vitepress.dev/reference/default-theme-home-page
layout: home

hero:
  text: "Hyprland extensions"
  tagline: Enhance your desktop capabilities with Pyprland
  image:
    src: ./logo.png
    alt: logo
  actions:
    - theme: brand
      text: Getting started
      link: /Getting-started
    - theme: alt
      text: Plugins
      link: /Plugins

features:
  - title: TOML format
    details: Simple but powerful configuration
  - title: Customizable
    details: Create your own Hyprland experience
  - title: Fast and easy
    details: Designed performance and ease of use
---

## What is Pyprland?

It's a software that extends the functionality of the great [Hyprland](https://hyprland.org/) window manager, adding new features and improving the existing ones.

It also enables a high degree of customization and automation, making it easier to adapt to your workflow.

To understand the potential of Pyprland, you can check the [plugins](/Plugins) page.

# Quick start

This process targets quick testing and not recommended in the long run, use your OS packages if possible.

Refer to the [Getting Started](/Getting-started) page for long term installation instructions.

## Install

> [!important]
> you'll need to install the `aiofiles` python package on your operating system first - _Pyprland_ depends on it.

You need to download [get-pypr](https://raw.githubusercontent.com/hyprland-community/pyprland/main/scripts/get-pypr) and run it with `sh` or `bash`, eg:

 ```sh
 curl https://raw.githubusercontent.com/hyprland-community/pyprland/main/scripts/get-pypr | sh
 ```

## Configure

Paste the content of the code blocks one after another in the same terminal:

 ```sh
cat <<EOF > ~/.config/hypr/pyprland.toml
```

 ```toml
[pyprland]

plugins = [
  "expose",
  "fetch_client_menu",
  "lost_windows",
  "magnify",
  "scratchpads",
  "shift_monitors",
  "toggle_special",
  "workspaces_follow_focus",
]

[pyprland.variables]
term_classed = "kitty --class"

[scratchpads.term]
animation = "fromTop"
command = "[term_classed] main-dropterm"
class = "main-dropterm"
size = "75% 60%"
max_size = "1920px 100%"
```

```sh
EOF

cat <<EOF >> ~/.config/hypr/hyprland.conf
exec-once = /usr/local/bin/pypr --debug /tmp/pypr.log
bind = \$mainMod, A, exec, pypr toggle term
bind = \$mainMod, B, exec, pypr expose
bind = \$mainMod, J, exec, pypr change_workspace -1
bind = \$mainMod, K, exec, pypr change_workspace +1
bind = \$mainMod, N, exec, pypr toggle_special minimized
bind = \$mainMod SHIFT, N, togglespecialworkspace, minimized
bind = \$mainMod SHIFT, O, exec, pypr shift_monitors +1
bind = \$mainMod SHIFT, Z, exec, pypr zoom ++0.5
bind = \$mainMod, Z, exec, pypr zoom
EOF
```

**Congratulations!**, you've installed and configured _Pyprland_.

Check the [plugins](/Plugins) page to understand how to configure and use each plugin.

## Uninstall

 ```sh
 sudo rm -fr /var/cache/pypr /usr/local/bin/pypr
 ```


