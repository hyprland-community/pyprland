---
commands:
    - name: wall next
      description: Changes the current background image, resume activity if paused
    - name: wall clear
      description: Removes the current background image and pause cycling
    - name: wall pause
      description: Stops updating the wallpaper automatically
    - name: wall color "#ff0000"
      description: Re-generate the [templates](#templates) with the given color
    - name: wall color "#ff0000" neutral
      description: Re-generate the templates with the given color and [color scheme](#color-scheme) (color filter)


---


# wallpapers

Search folders for images and sets the background image at a regular interval.
Pictures are selected randomly from the full list of images found.

It serves two purposes:

- adding support for random images to any background setting tool
- quickly testing different tools with a minimal effort

It allows "zapping" current backgrounds, clearing it to go distraction free and optionally make them different for each screen.

> [!tip]
> Uses **hyprpaper** by default, but can be configured to use any other application.
> You'll need to run hyprpaper separately for now. (eg: `uwsm app -- hyprpaper`)

## Niri support

Niri is supported, but you must ensure that you are using a wallpaper manager that supports it (eg: `swww`).

```toml
[wallpapers]
path = "/home/me/Pictures/Wallpapers"
command = "swww img [file]"
```

<details>
    <summary>Minimal example using defaults (requires <b>hyprpaper</b>)</summary>

```toml
[wallpapers]
path = "~/Pictures/wallpapers/" # path to the folder with background images
```

</details>

<details>
<summary>More complete, using the custom <b>swww</b> command (not recommended because of its stability)</summary>

```toml
[wallpapers]
unique = true # set a different wallpaper for each screen
path = "~/Pictures/wallpapers/"
interval = 60 # change every hour
extensions = ["jpg", "jpeg"]
recurse = true
clear_command = "swww clear"
command = "swww img --outputs '[output]'  '[file]'"

```

Note that for applications like `swww`, you'll need to start a daemon separately (eg: from `hyprland.conf`).
</details>


## Commands

<CommandList :commands="$frontmatter.commands" />

## Configuration

### `path` <Badge type="danger" text="required" />

path to a folder or list of folders that will be searched. Can also be a list, eg:

```toml
path = ["~/Pictures/Portraits/", "~/Pictures/Landscapes/"]
```

### `interval`

defaults to `10`

How long (in minutes) a background should stay in place


### `command`

Overrides the default command to set the background image.

> [!note]
> Uses an optimized **hyprpaper** usage if *no command* is provided on version > 2.5.1

[variables](./Variables) are replaced with the appropriate values, you must use a `"[file]"` placeholder for the image path and `"[output]"` for the screen. eg:

```sh
swaybg -i '[file]' -o '[output]'
```
or
```sh
swww img --outputs [output]  [file]
```

### `clear_command`

By default `clear` command kills the `command` program.

Instead of that, you can provide a command to clear the background. eg:

```toml
clear_command = "swaybg clear"
```

### `post_command`

Executes a command after a wallpaper change. Can use `[file]`, eg:

```toml
post_command = "matugen image '[file]'"
```

### `radius`

When set, adds rounded borders to the wallpapers. Expressed in pixels. Disabled by default.

For this feature to work, you must use '[output]' in your `command` to specify the screen port name to use in the command.

eg:
```toml
radius = 16
```

### `extensions`

defaults to `["png", "jpg", "jpeg"]`

List of valid wallpaper image extensions.

### `recurse`

defaults to `false`

When enabled, will also search sub-directories recursively.

### `unique`

defaults to `false`

When enabled, will set a different wallpaper for each screen (Usage with [templates](#templates) is not recommended).

If you are not using the default application, ensure you are using `"[output]"` in the [command](#command) template.

Example for swaybg: `swaybg -o "[output]" -m fill -i "[file]"`

### `templates`

Minimal *matugen* or *pywal* feature, mostly compatible with *matugen* syntax.

Open a ticket if misses a feature you are used to.

Example:
``` toml
[wallpapers.templates.hyprland]
input_path = "~/color_configs/hyprlandcolors.sh"
output_path = "/tmp/hyprlandcolors.sh"
post_hook = "sh /tmp/hyprlandcolors.sh"
```

Where the input_path would contain
```sh
hyprctl keyword general:col.active_border "rgb({{colors.primary.default.hex_stripped}}) rgb({{colors.tertiary.default.hex_stripped}}) 30deg"
hyprctl keyword decoration:shadow:color "rgb({{colors.primary.default.hex_stripped}})"
```

#### Supported transformations:

- set_lightness
- set_alpha

#### Supported color formats:

- hex
- hex_stripped
- rgb
- rgba

#### Supported colors:

- source
- primary
- on_primary
- primary_container
- on_primary_container
- secondary
- on_secondary
- secondary_container
- on_secondary_container
- tertiary
- on_tertiary
- tertiary_container
- on_tertiary_container
- error
- on_error
- error_container
- on_error_container
- surface
- surface_bright
- surface_dim
- surface_container_lowest
- surface_container_low
- surface_container
- surface_container_high
- surface_container_highest
- on_surface
- surface_variant
- on_surface_variant
- background
- on_background
- outline
- outline_variant
- inverse_primary
- inverse_surface
- inverse_on_surface
- surface_tint
- scrim
- shadow
- white
- primary_fixed
- primary_fixed_dim
- on_primary_fixed
- on_primary_fixed_variant
- secondary_fixed
- secondary_fixed_dim
- on_secondary_fixed
- on_secondary_fixed_variant
- tertiary_fixed
- tertiary_fixed_dim
- on_tertiary_fixed
- on_tertiary_fixed_variant
- red
- green
- yellow
- blue
- magenta
- cyan

### `color_scheme`

Optional modification of the base color used in the [templates](#templates). One of:

- **pastel** a bit more washed colors
- **fluo** or **fluorescent** for high color saturation
- **neutral** for low color saturation
- **earth** a bit more dark, a bit less blue
- **vibrant** for moderate to high saturation
- **mellow** for lower saturation

### `variant`

Changes the algorithm in use to pick the primary, secondary and tertiary colors.

- "islands" will use the 3 most popular colors of the wallpaper image

otherwise it will only pick the "main" color and shift the hue to get the secondary and tertiary colors.
