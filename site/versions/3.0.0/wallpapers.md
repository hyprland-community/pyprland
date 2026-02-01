---
---


# wallpapers

Search folders for images and sets the background image at a regular interval.
Pictures are selected randomly from the full list of images found.

It serves few purposes:

- adding support for random images to any background setting tool
- quickly testing different tools with a minimal effort
- adding rounded corners to each wallpaper screen
- generating a wallpaper-compliant color scheme usable to generate configurations for any application (matugen/pywal alike)

It allows "zapping" current backgrounds, clearing it to go distraction free and optionally make them different for each screen.

> [!important]
> On Hyprland, Pyprland uses **hyprpaper** by default, but you must start hyprpaper separately (e.g. `uwsm app -- hyprpaper`). For other environments, set the `command` option to launch your wallpaper application.

> [!note]
> On environments other than Hyprland and Niri, pyprland uses `wlr-randr` (Wayland) or `xrandr` (X11) for monitor detection.
> This provides full wallpaper functionality but without automatic refresh on monitor hotplug.

Cached images (rounded corners, online downloads) are stored in subfolders within your configured `path` directory.

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

<PluginCommands plugin="wallpapers" />

> [!tip]
> The `color` and `palette` commands are used for templating. See [Templates](./wallpapers_templates#commands) for details.

## Configuration

<PluginConfig plugin="wallpapers" linkPrefix="config-" :filter="['path', 'interval', 'command', 'clear_command', 'post_command', 'radius', 'extensions', 'recurse', 'unique']" />

### `path` <ConfigBadges plugin="wallpapers" option="path" /> {#config-path}

**Required.** Path to a folder or list of folders that will be searched for wallpaper images.

```toml
path = ["~/Pictures/Portraits/", "~/Pictures/Landscapes/"]
```

### `interval` <ConfigBadges plugin="wallpapers" option="interval" /> {#config-interval}

How long (in minutes) a background should stay in place before changing.

### `command` <ConfigBadges plugin="wallpapers" option="command" /> {#config-command}

Overrides the default command to set the background image.

> [!important]
> **Required** for all environments except Hyprland.
> On Hyprland, defaults to using hyprpaper if not specified.

[Variables](./Variables) are replaced with the appropriate values. Use `[file]` for the image path and `[output]` for the monitor name:

> [!note]
> The `[output]` variable requires monitor detection (available on Hyprland, Niri, and fallback environments with `wlr-randr` or `xrandr`).

```sh
swaybg -i '[file]' -o '[output]'
```
or
```sh
swww img --outputs [output] [file]
```

### `clear_command` <ConfigBadges plugin="wallpapers" option="clear_command" /> {#config-clear-command}

Overrides the default behavior which kills the `command` program.
Use this to provide a command to clear the background:

```toml
clear_command = "swaybg clear"
```

### `post_command` <ConfigBadges plugin="wallpapers" option="post_command" /> {#config-post-command}

Executes a command after a wallpaper change. Can use `[file]`:

```toml
post_command = "matugen image '[file]'"
```

### `radius` <ConfigBadges plugin="wallpapers" option="radius" /> {#config-radius}

When set, adds rounded borders to the wallpapers. Expressed in pixels. Disabled by default.

Requires monitor detection (available on Hyprland, Niri, and fallback environments with `wlr-randr` or `xrandr`).
For this feature to work, you must use `[output]` in your `command` to specify the screen port name.

```toml
radius = 16
```

### `extensions` <ConfigBadges plugin="wallpapers" option="extensions" /> {#config-extensions}

List of valid wallpaper image extensions.

### `recurse` <ConfigBadges plugin="wallpapers" option="recurse" /> {#config-recurse}

When enabled, will also search sub-directories recursively.

### `unique` <ConfigBadges plugin="wallpapers" option="unique" /> {#config-unique}

When enabled, will set a different wallpaper for each screen.

> [!note]
> Requires monitor detection (available on Hyprland, Niri, and fallback environments with `wlr-randr` or `xrandr`).
> Usage with [templates](./wallpapers_templates) is not recommended.

If you are not using the default application, ensure you are using `[output]` in the [command](#config-command) template.

Example for swaybg: `swaybg -o "[output]" -m fill -i "[file]"`

## Online Wallpapers

Pyprland can fetch wallpapers from free online sources like Unsplash, Wallhaven, Reddit, and more. Downloaded images are stored locally and become part of your collection.

See [Online Wallpapers](./wallpapers_online) for configuration options and available backends.

## Templates

Generate config files with colors extracted from your wallpaper - similar to matugen/pywal. Automatically theme your terminal, window borders, GTK apps, and more.

See [Templates](./wallpapers_templates) for full documentation including syntax, color reference, and examples.
