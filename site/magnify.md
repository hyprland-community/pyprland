---
---
# magnify

Zooms in and out with an optional animation.


<details>
    <summary>Example</summary>

```sh
pypr zoom  # sets zoom to `factor`
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

## Commands

<PluginCommands plugin="magnify" />

### `zoom [factor]`

#### unset / not specified

Will zoom to [factor](#config-factor) if not zoomed, else will set the zoom to 1x.

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

<PluginConfig plugin="magnify" linkPrefix="config-" />

### `factor` {#config-factor}

<ConfigDefault plugin="magnify" option="factor" />

The zoom level to use when `pypr zoom` is called without arguments.

### `duration` {#config-duration}

<ConfigDefault plugin="magnify" option="duration" />

Animation duration in seconds. Not needed with recent Hyprland versions - you can customize the animation in Hyprland config instead:

```C
animations {
    bezier = easeInOut,0.65, 0, 0.35, 1
    animation = zoomFactor, 1, 4, easeInOut
}
```
