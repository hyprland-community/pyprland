# Getting started

Pypr consists in two things:

- **a tool**: `pypr` which runs the daemon (service), but also allows to interact with it
- **some config file**: `~/.config/hypr/pyprland.toml` (or the path set using `--config`) using the [TOML](https://toml.io/en/) format

The `pypr` tool only have a few built-in commands:

- `help` lists available commands (including plugins commands)
- `exit` will terminate the service process
- `edit` edit the configuration using your `$EDITOR` (or `vi`), reloads on exit - added in 2.2.4
- `dumpjson` shows a JSON representation of the configuration (after other files have been `include`d) - added in 2.2.11
- `reload` reads the configuration file and apply some changes:
  - new plugins will be loaded
  - configuration items will be updated (most plugins will use the new values on the next usage)

Other commands are implemented by adding [plugins](Plugins).

> [!important]
> - with no argument it runs the daemon (doesn't fork in the background)
>
> - if you pass parameters, it will interact with the daemon instead.

> [!note]
> Pypr *command* names are documented using underscores (`_`) but you can use dashes (`-`) instead.
> Eg: `pypr shift_monitors` and `pypr shift-monitors` will run the same command


## Configuration file

The configuration file uses a [TOML format](https://toml.io/) with the following as the bare minimum:

```toml
[pyprland]
plugins = ["plugin_name", "other_plugin"]
```

Additionally some plugins require **Configuration** options, using the following format:

```toml
[plugin_name]
plugin_option = 42

[plugin_name.another_plugin_option]
suboption = "config value"
```

### Multiple configuration files

You can also split your configuration into multiple files that will be loaded in the provided order after the main file (added in 2.2.4):
```toml
[pyprland]
include = ["/shared/pyprland.toml", "~/pypr_extra_config.toml"]
```
Since 2.2.16 you can also load folders, in which case TOML files in the folder will be loaded in alphabetical order:
```toml
[pyprland]
include = ["~/.config/pypr.d/"]
```

And then add a `~/.config/pypr.d/monitors.toml` file:
```toml
pyprland.plugins = [ "monitors" ]

[monitors.placement]
BenQ.Top_Center_Of = "DP-1" # projo
"CJFH277Q3HCB".top_of = "eDP-1" # work
```

> [!note]
> To check the final merged configuration, you can use the `dumpjson` command.

## Installation

Check your OS package manager first, eg:

- Archlinux: you can find it on AUR, eg with [yay](https://github.com/Jguer/yay): `yay pyprland`
- NixOS: Instructions in the [Nix](Nix) page

Otherwise, use the python package manager *inside a virtual environment* (`python -m venv somefolder && source ./somefolder/bin/activate`):

```sh
pip install pyprland
```

> [!tip]
> In case you don't want to deal with `pip` or `virtualenv` and don't have it in your package manager, ensure you have `asyncio` python package installed and use the following command:
>
> ```sh
> curl https://raw.githubusercontent.com/hyprland-community/pyprland/main/scripts/get-pypr | sh
> ```
> To **completely** remove it from your system, run:
> ```sh
> sudo rm -fr /var/cache/pypr /usr/local/bin/pypr
> ```


## Running

> [!warning]
> If you messed with something else than your OS packaging system to get `pypr` installed, use the full path to the `pypr` command.

Preferably start the process with hyprland, adding to `hyprland.conf`:

```ini
exec-once = /usr/bin/pypr
```

or if you run into troubles (use the first version once your configuration is stable):

```ini
exec-once = /usr/bin/pypr --debug /tmp/pypr.log
```

> [!note]
> To avoid issues (eg: you have a complex setup, maybe using a virtual environment), you may want to set the full path (eg: `/home/bob/venv/bin/pypr`).
> You can get it from `which pypr` in a working terminal

Once the `pypr` daemon is started (cf `exec-once`), you can list the eventual commands which have been added by the plugins using `pypr -h` or `pypr help`, those commands are generally meant to be use via key bindings, see the `hyprland.conf` part of *Configuring* section below.

## Configuring

Create a configuration file in `~/.config/hypr/pyprland.toml` enabling a list of plugins, each plugin may have its own configuration needs or don't need any configuration at all. Most default values should be okay, just set when you are not satisfied with the default.

Check the [TOML format](https://toml.io/) for details about the syntax.

Simple example:

```toml
[pyprland]
plugins = [
    "shift_monitors",
    "workspaces_follow_focus"
]
```

More complex example:

```toml
[pyprland]
plugins = [
  "scratchpads",
  "lost_windows",
  "monitors",
  "toggle_dpms",
  "magnify",
  "expose",
  "shift_monitors",
  "workspaces_follow_focus",
]

[monitors.placement]
"Acer".top_center_of = "Sony"

[workspaces_follow_focus]
max_workspaces = 9

[expose]
include_special = false

[scratchpads.stb]
animation = "fromBottom"
command = "kitty --class kitty-stb sstb"
class = "kitty-stb"
lazy = true
size = "75% 45%"

[scratchpads.stb-logs]
animation = "fromTop"
command = "kitty --class kitty-stb-logs stbLog"
class = "kitty-stb-logs"
lazy = true
size = "75% 40%"

[scratchpads.term]
animation = "fromTop"
command = "kitty --class kitty-dropterm"
class = "kitty-dropterm"
size = "75% 60%"

[scratchpads.volume]
animation = "fromRight"
command = "pavucontrol"
class = "org.pulseaudio.pavucontrol"
lazy = true
size = "40% 90%"
unfocus = "hide"
```

Some of those plugins may require changes in your `hyprland.conf` to fully operate or to provide a convenient access to a command, eg:

```bash
bind = $mainMod SHIFT, Z, exec, pypr zoom
bind = $mainMod ALT, P,exec, pypr toggle_dpms
bind = $mainMod SHIFT, O, exec, pypr shift_monitors +1
bind = $mainMod, B, exec, pypr expose
bind = $mainMod, K, exec, pypr change_workspace +1
bind = $mainMod, J, exec, pypr change_workspace -1
bind = $mainMod,L,exec, pypr toggle_dpms
bind = $mainMod SHIFT,M,exec,pypr toggle stb stb-logs
bind = $mainMod,A,exec,pypr toggle term
bind = $mainMod,V,exec,pypr toggle volume
```

> [!tip]
> Consult or share [configuration files](https://github.com/hyprland-community/pyprland/tree/main/examples)

## Optimization

### Plugins

Only enable the plugins you are using in the `plugins` array (in `[pyprland]` section).

Leaving the configuration for plugins which are not enabled will have no impact.

### Pypr command

In case you want to save some time when interacting with the daemon
you can use `socat` instead (needs to be installed). Example of a `pypr-cli` command (should be reachable from your environment's `PATH`):
```sh
#!/bin/sh
socat - "UNIX-CONNECT:/tmp/hypr/${HYPRLAND_INSTANCE_SIGNATURE}/.pyprland.sock" <<< $@
```
On slow systems this may make a difference.
Note that the "help" command will require usage of the standard `pypr` command.

## Troubleshoot

You can enable debug logging and saving to file using the `--debug` argument, eg:

```sh
pypr --debug /tmp/pypr.log
```

More info in the [troubleshooting](Troubleshooting) page.

