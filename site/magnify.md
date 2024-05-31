# Command

- `zoom [value]`
    - If no value is provided, toggles magnification.
    - If an integer is provided, it will set as scaling factor.
    - If this integer is prefixed with "+" or "-", it will *update* the current scale factor (added in version 2.1.4).
        - Use "++" or "--", to use a more natural non-linear scale (added in version 2.2.9).

> [!NOTE]
>
> The non-linear scale is calculated as powers of two, eg:
>
> - `zoom ++1` → 2x, 4x, 8x, 16x...
> - `zoom ++0.7` → 1.6x, 2.6x, 4.3x, 7.0x, 11.3x, 18.4x...
> - `zoom ++0.5` → 1.4x, 2x, 2.8x, 4x, 5.7x, 8x, 11.3x, 16x...

# Configuration

Sample `hyprland.conf`:

```sh
bind = $mainMod , Z, exec, pypr zoom ++0.5
bind = $mainMod SHIFT, Z, exec, pypr zoom
```


## `factor` (optional)

default value is `2`

Scaling factor to be used when no value is provided.

# Example

```sh
pypr zoom  # sets zoom to `factor` (2 by default)
pypr zoom +1  # will set zoom to 3x
pypr zoom  # will set zoom to 1x
pypr zoom 1 # will (also) set zoom to 1x - effectively doing nothing
```

## `duration` (optional)

> _Added in version 2.2.9_

Default value is `15`

Duration in tenths of a second for the zoom animation to last, set to `0` to disable animations.
