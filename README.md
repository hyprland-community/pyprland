# Pyprland

## Scratchpads, smart monitor placement and other tweaks for hyprland

Host process for multiple Hyprland plugins.

- **tool**: `pypr`
- **config file**: `~/.config/hypr/pyprland.json`

The `pypr` tool only have two built-in commands:

- `reload` reads the configuration file and attempt to apply the changes
- `--help` lists available commands (including plugins commands)

Other commands are added by adding plugins.

A single config file `~/.config/hypr/pyprland.json` is used, using the following syntax:

```json
{
  "pyprland": {
    "plugins": ["plugin_name"]
  },
  "plugin_name": {
    "plugin_option": 42
  }
}
```

## Built-in plugins

- `scratchpads` implements dropdowns & togglable poppups
- `monitors` allows relative placement of monitors depending on the model
- `workspaces_follow_focus` provides commands and handlers allowing a more flexible workspaces usage on multi-monitor setups. If you think the multi-screen behavior of hyprland is not usable or broken/unexpected, this is probably for you.
- `lost_windows` brings lost floating windows to the current workspace
- `toggle_dpms` toggles the DPMS status of every plugged monitor
- `magnify` toggles zooming of viewport or sets a specific scaling factor
- `shift_monitors` adds a self-configured "swapactiveworkspaces" command

## Installation

Use the python package manager:

```
pip install pyprland
```

If you run archlinux, you can also find it on AUR: `yay -S pyprland`

Don't forget to start the process with hyprland, adding to `hyprland.conf`:

```
exec-once = pypr
```

## Getting started

Create a configuration file in `~/.config/hypr/pyprland.json` enabling a list of plugins, each plugin may have its own configuration needs, eg:

```json
{
  "pyprland": {
    "plugins": [
      "scratchpads",
      "monitors",
      "workspaces_follow_focus"
    ]
  },
  "scratchpads": {
    "term": {
      "command": "kitty --class kitty-dropterm",
      "animation": "fromTop",
      "unfocus": "hide"
    },
    "volume": {
      "command": "pavucontrol",
      "unfocus": "hide",
      "animation": "fromRight"
    }
  },
  "monitors": {
    "placement": {
      "BenQ PJ": {
        "topOf": "eDP-1"
      }
    }
    "unknown": "wlrlui"
  }
}
```

# Plugin: `shift_monitors`

Swaps the workspaces of every screen in the given direction.
Note the behavior can be hard to predict if you have more than 2 monitors, suggestions are welcome.

### Command

- `shift_monitors <direction>`: swaps every monitor's workspace in the given direction

Example usage in `hyprland.conf`:

```
bind = $mainMod SHIFT, O, exec, pypr shift_monitors +1
 ```

# Plugin: `magnify`

### Command

- `zoom [value]`: if no value, toggles magnification. If an integer is provided, it will set as scaling factor.

### Configuration


#### `factor` (optional, defaults to 2)

Scaling factor to be used when no value is provided.

# Plugin: `toggle_dpms`

### Command

- `toggle_dpms`: if any screen is powered on, turn them all off, else turn them all on


# Plugin: `lost_windows`

### Command

- `attract_lost`: brings the lost windows to the current screen / workspace

# Plugin: `monitors`

Syntax:
```json
"monitors": {
  "placement": {
    "<partial model description>": {
      "placement type": "<monitor name/output>"
    },
    "unknown": "<command to run for unknown monitors>"
  }
}
```

Example:
```json
"monitors": {
  "unknown": "notify-send 'Unknown monitor'",
  "placement": {
    "Sony": {
      "topOf": "HDMI-1"
    }
  }
}
```

Requires `wlr-randr`.

Allows relative placement of monitors depending on the model ("description" returned by `hyprctl monitors`).

### Configuration


#### `placement`

Supported placements are:

- leftOf
- topOf
- rightOf
- bottomOf

#### `unknown` (optional)

If set, runs the associated command for screens which aren't matching any of the provided placements (pattern isn't found in monitor description).

**Note** this is supposed to be a short lived command which will block the rest of the process until closed. In other words no plugin will be processed while this command remains open.

# Plugin: `workspaces_follow_focus`

Make non-visible workspaces follow the focused monitor.
Also provides commands to switch between workspaces wile preserving the current monitor assignments: 

Syntax:
```json
"workspaces_follow_focus": {
  "max_workspaces": <number of workspaces>
}
```

### Command

- `change_workspace` `<direction>`: changes the workspace of the focused monitor

Example usage in `hyprland.conf`:

```
bind = $mainMod, K, exec, pypr change_workspace +1
bind = $mainMod, J, exec, pypr change_workspace -1
 ```

### Configuration

You can set the `max_workspaces` property, defaults to `10`.

# Plugin: `scratchpads`

Defines commands that should run in dropdowns. Successor of [hpr-scratcher](https://github.com/hyprland-community/hpr-scratcher), it's fully compatible, just put the configuration under "scratchpads".

Syntax:
```json
"scratchpads": {
  "scratchpad name": {
    "command": "command to run"
  }
}
```

As an example, defining two scratchpads:

- _term_ which would be a kitty terminal on upper part of the screen
- _volume_ which would be a pavucontrol window on the right part of the screen

Example:
```json
"scratchpads": {
  "term": {
    "command": "kitty --class kitty-dropterm",
    "animation": "fromTop",
    "margin": 50,
    "unfocus": "hide"
  },
  "volume": {
    "command": "pavucontrol",
    "animation": "fromRight"
  }
}
```

In your `hyprland.conf` add something like this:

```ini
exec-once = hpr-scratcher

# Repeat this for each scratchpad you need
bind = $mainMod,V,exec,hpr-scratcher toggle volume
windowrule = float,^(pavucontrol)$
windowrule = workspace special silent,^(pavucontrol)$

bind = $mainMod,A,exec,hpr-scratcher toggle term
$dropterm  = ^(kitty-dropterm)$
windowrule = float,$dropterm
windowrule = workspace special silent,$dropterm
windowrule = size 75% 60%,$dropterm
```

And you'll be able to toggle pavucontrol with MOD + V.

### Commands

- `toggle <scratchpad name>` : toggle the given scratchpad
- `show <scratchpad name>` : show the given scratchpad
- `hide <scratchpad name>` : hide the given scratchpad

Note: with no argument it runs the daemon (doesn't fork in the background)



### Configuration

#### `command`

This is the command you wish to run in the scratchpad.
For a nice startup you need to be able to identify this window in `hyprland.conf`, using `--class` is often a good idea.

#### `animation` (optional)

Type of animation to use

- `null` / `""` / not defined (no animation)
- "fromTop" (stays close to top screen border)
- "fromBottom" (stays close to bottom screen border)
- "fromLeft" (stays close to left screen border)
- "fromRight" (stays close to right screen border)

#### `offset` (optional)

number of pixels for the animation.

#### `unfocus` (optional)

allow to hide the window when the focus is lost when set to "hide"

#### `margin` (optional)

number of pixels separating the scratchpad from the screen border

# Writing plugins

You can start enabling a plugin called "experimental" and add code to `plugins/experimental.py`.
A better way is to copy this as a starting point and make your own python module.
Plugins can be loaded with full python module path, eg: `"mymodule.pyprlandplugin"`, the loaded module must provide an `Extension` interface.

Check the `interface.py` file to know the base methods, also have a look at the other plugins for working examples.

To get more details when an error is occurring, `export DEBUG=1` in your shell before running.

## Creating a command

Just add a method called `run_<name of your command>`, eg with "togglezoom" command:

```python
async def init(self):
  self.zoomed = False

async def run_togglezoom(self, args):
  if self.zoomed:
    await hyprctl('misc:cursor_zoom_factor 1', 'keyword')
  else:
    await hyprctl('misc:cursor_zoom_factor 2', 'keyword')
  self.zoomed = not self.zoomed
```

## Reacting to an event

Similar as a command, implement some `event_<the event you are interested in>` method.

