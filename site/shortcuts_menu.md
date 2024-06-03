# shortcuts_menu

Presents some menu to run shortcut commands. Supports nested menus (aka categories / sub-menus).

<details>
   <summary>Configuration example</summary>

```toml
[shortcuts_menu.entries]

"Open Jira ticket" = 'open-jira-ticket "$(wl-paste)"'
Relayout = "pypr relayout"
"Fetch window" = "pypr fetch_client_menu"
"Hyprland socket" = 'kitty  socat - "UNIX-CONNECT:$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket2.sock"'
"Hyprland logs" = 'kitty tail -f $XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/hyprland.log'

"Serial USB Term" = [
    {name="device", command="ls -1 /dev/ttyUSB*; ls -1 /dev/ttyACM*"},
    {name="speed", options=["115200", "9600", "38400", "115200", "256000", "512000"]},
    "kitty miniterm --raw --eol LF [device] [speed]"
]

"Color picker" = [
    {name="format", options=["hex", "rgb", "hsv", "hsl", "cmyk"]},
    "sleep 0.2; hyprpicker --format [format] | wl-copy" # sleep to let the menu close before the picker opens
]
```

</details>


## Command

- `menu [name]`: shows a list of options which have been configured in "entries".

  If "name" is provided it will show the given sub-menu.

  - You can use "." to reach any level of the configured menus.
      Example to reach `[shortcuts_menu.entries.utils."local commands"]`:
      ```sh
       pypr menu "utils.local commands"
      ```

## Configuration

All the [Menu](Menu) configuration items are also available.

### `entries`

Defines the menu entries. Supports [Variables](Variables)

```toml
[shortcuts_menu.entries]
"entry 1" = "command to run"
"entry 2" = "command to run"
```
Submenus can be defined too (there is no depth limit):

```toml
[shortcuts_menu.entries."My submenu"]
"entry X" = "command"

[shortcuts_menu.entries.one.two.three.four.five]
foobar = "ls"
```

#### Advanced usage

Instead of navigating a configured list of menu options and running a pre-defined command, you can collect various *variables* (either static list of options selected by the user, or generated from a shell command) and then run a command using those variables. Eg:

```toml
"Play Video" = [
    {name="video_device", command="ls -1 /dev/video*"},
    {name="player",
        options=["mpv", "guvcview"]
    },
    "[player] [video_device]"
]

"Ssh" = [
    {name="action", options=["htop", "uptime", "sudo halt -p"]},
    {name="host", options=["gamix", "gate", "idp"]},
    "kitty --hold ssh [host] [action]"
]
```

You must define a list of objects, containing:
- `name`: the variable name
- then the list of options, must one of:
    - `options` for a static list of options
    - `command` to get the list of options from a shell command's output

> [!tip]
> You can apply post-filters to the `command` output, eg:
> ```toml
> {name="entry", command="cliphist list", filter="s/\t.*//"},
> ```
> check the [filters](filters) page for more details

The last item of the list must be a string which is the command to run. Variables can be used enclosed in `[]`.

### `command_start` & `command_end` / `submenu_start` & `submenu_end`

Allow adding some text (eg: icon) before / after a menu entry.

command_* is for final commands, while submenu_* is for entries leading to another menu.

By default `submenu_end` is set to a right arrow sign, while other attributes are not set.

### `skip_single` (optional)

Defaults to `true`.
When disabled, shows the menu even for single options

## Hints

### Multiple menus

To manage multiple distinct menus, always use a name when using the `pypr menu <name>` command.

Example of a multi-menu configuration:

```toml
[shortcuts_menu.entries."Basic commands"]
"entry X" = "command"
"entry Y" = "command2"

[shortcuts_menu.entries.menu2]
## ...
```

You can then show the first menu using `pypr menu "Basic commands"`
