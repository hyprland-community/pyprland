---
commands:
    - name: wall next
      description: Changes the current background image
    - name: wall clear
      description: Removes the current background image
---

# wallpapers

Search folders for images and sets the background image at a regular interval.
Images are selected randomly from the full list of images found.

It serves two purposes:

- adding support for random images to any background setting tool
- quickly testing different tools with a minimal effort

It allows "zapping" current backgrounds, clearing it to go distraction free and optionally make them different for each screen.

> [!tip]
> Uses **swaybg** by default, but can be configured to use any other application.

<details>
    <summary>Minimal example using defaults(requires <b>swaybg</b>)</summary>

```toml
[wallpapers]
path = "~/Images/wallpapers/" # path to the folder with background images
```

</details>

<details>
<summary>More complete, using the custom <b>swww</b> command (not recommended because of its stability)</summary>

```toml
[wallpapers]
unique = true # set a different wallpaper for each screen
path = "~/Images/wallpapers/"
interval = 60 # change every hour
extensions = ["jpg", "jpeg"]
recurse = true
## Using swww
command = 'swww img --transition-type any "[file]"'
clear_command = "swww clear"
```

Note that for applications like `swww`, you'll need to start a daemon separately (eg: from `hyprland.conf`).
</details>


## Commands

<CommandList :commands="$frontmatter.commands" />

## Configuration


### `path` (REQUIRED)

path to a folder or list of folders that will be searched. Can also be a list, eg:

```toml
path = ["~/Images/Portraits/", "~/Images/Landscapes/"]
```

### `interval`

defaults to `10`

How long (in minutes) a background should stay in place


### `command`

Overrides the default command to set the background image.

[variables](./Variables) are replaced with the appropriate values, you must use a `"[file]"` placeholder for the image path and `"[output]"` for the screen. eg:

```
swaybg -m fill -i "[file]" -o "[output]"
```

### `clear_command`

By default `clear` command kills the `command` program.

Instead of that, you can provide a command to clear the background. eg:

```
clear_command = "swaybg clear"
```

### `post_command`

Executes a command after a wallpaper change. Can use `[file]`.

```
post_command = "matugen image [file]"
```

### `radius`

When set, adds rounded borders to the wallpapers. Expressed in pixels. Disabled by default.

```
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

When enabled, will set a different wallpaper for each screen.

If you are not using the default application, ensure you are using `"[output]"` in the [command](#command) template.

Example for swaybg: `swaybg -o "[output]" -m fill -i "[file]"`
