---
commands:
    - name: zoom [value]
      description: Set the current zoom level (absolute or relative) - toggle zooming if no value is provided
---
# magnify

Zooms in and out with an optional animation.


<details>
    <summary>Example</summary>

```sh
pypr zoom  # sets zoom to `factor` (2 by default)
pypr zoom +1  # will set zoom to 3x
pypr zoom  # will set zoom to 1x
pypr zoom 1 # will (also) set zoom to 1x - effectively doing nothing
```

Sample `hyprland.conf`:

```sh
bind = $mainMod , Z, exec, pypr zoom ++0.5
bind = $mainMod SHIFT, Z, exec, pypr zoom
```

</details>

## Command

<CommandList :commands="$frontmatter.commands" />

### `[value]`

#### unset / not specified

Will zoom to [factor](#factor-optional) if not zoomed, else will set the zoom to 1x.

#### floating or integer value

Will set the zoom to the provided value.

#### +value / -value

Update (increment or decrement) the current zoom level by the provided value.

#### ++value / --value

Update (increment or decrement) the current zoom level by a non-linear scale.
It _looks_ more linear changes than using a single + or -.

> [!NOTE]
>
> The non-linear scale is calculated as powers of two, eg:
>
> - `zoom ++1` → 2x, 4x, 8x, 16x...
> - `zoom ++0.7` → 1.6x, 2.6x, 4.3x, 7.0x, 11.3x, 18.4x...
> - `zoom ++0.5` → 1.4x, 2x, 2.8x, 4x, 5.7x, 8x, 11.3x, 16x...

## Configuration

### `factor`

default value is `2`

Scaling factor to be used when no value is provided.

### `duration`

Default value is `0`

Duration in tenths of a second for the zoom animation to last, set to `15` for the former behavior.
It is not needed anymore with recent Hyprland versions, you can even customize the animation in use:

in *Hyprland* config:
```
animations {
    bezier = easeInOut,0.65, 0, 0.35, 1
    animation = zoomFactor, 1, 4, easeInOut
}
```
