# Extensions & tweaks for hyprland

Host process for multiple Hyprland plugins.
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

Built-in plugins are:

- `scratchpad` implements dropdowns & togglable poppups
- `monitors` allows relative placement of monitors depending on the model
- `workspaces_follow_focus` provides commands and handlers allowing a more flexible workspaces usage on multi-monitor setups

## Installation

```
pip install pyprland
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
      "class": "kitty-dropterm",
      "animation": "fromTop",
      "unfocus": "hide"
    },
    "volume": {
      "command": "pavucontrol",
      "class": "pavucontrol",
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
  }
}
```

# Configuring plugins

## `monitors`

Requires `wlr-randr`.

Allows relative placement of monitors depending on the model ("description" returned by `hyprctl monitors`).

### Configuration

Supported placements are:

- leftOf
- topOf
- rightOf
- bottomOf

## `workspaces_follow_focus`

Make non-visible workspaces follow the focused monitor.
Also provides commands to switch between workspaces wile preserving the current monitor assignments: 

### Commands

- `change_workspace` `<direction>`: changes the workspace of the focused monitor

Example usage in `hyprland.conf`:

```
bind = $mainMod, K, exec, pypr change_workspace +1
bind = $mainMod, J, exec, pypr change_workspace -1
 ```

### Configuration

You can set the `max_workspaces` property, defaults to `10`.

## `scratchpads`

Check [hpr-scratcher](https://github.com/hyprland-community/hpr-scratcher), it's fully compatible, just put the configuration under "scratchpads".

As an example, defining two scratchpads:

- _term_ which would be a kitty terminal on upper part of the screen
- _volume_ which would be a pavucontrol window on the right part of the screen

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

Then in the configuration file, add something like this:

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

And you'll be able to toggle pavucontrol with MOD + V.

### Command-line options

- `reload` : reloads the configuration file
- `toggle <scratchpad name>` : toggle the given scratchpad
- `show <scratchpad name>` : show the given scratchpad
- `hide <scratchpad name>` : hide the given scratchpad

Note: with no argument it runs the daemon (doesn't fork in the background)

### Scratchpad Options

#### command

This is the command you wish to run in the scratchpad.
For a nice startup you need to be able to identify this window in `hyprland.conf`, using `--class` is often a good idea.

#### animation

Type of animation to use

- `null` / `""` / not defined
- "fromTop"
- "fromBottom"
- "fromLeft"
- "fromRight"

#### offset (optional)

number of pixels for the animation.

#### unfocus (optional)

allow to hide the window when the focus is lost when set to "hide"

#### margin (optional)

number of pixels separating the scratchpad from the screen border
