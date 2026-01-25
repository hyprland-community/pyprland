---
---

# monitors

Allows relative placement of monitors depending on the model ("description" returned by `hyprctl monitors`).
Useful if you have multiple monitors connected to a video signal switch or using a laptop and plugging monitors having different relative positions.

> [!Tip]
> This plugin also supports Niri. It will automatically detect the environment and use `nirictl` to apply the layout.
> Note that "hotplug_commands" and "unknown" commands may need adjustment for Niri (e.g. using `sh -c '...'` or Niri specific tools).

Syntax:


```toml
[monitors.placement]
"description match".placement = "other description match"
```

<details>
    <summary>Example to set a Sony monitor on top of a BenQ monitor</summary>

```toml
[monitors.placement]
Sony.topOf = "BenQ"

## Character case is ignored, "_" can be added
Sony.Top_Of = ["BenQ"]

## Thanks to TOML format, complex configurations can use separate "sections" for clarity, eg:

[monitors.placement."My monitor brand"]
## You can also use "port" names such as *HDMI-A-1*, *DP-1*, etc...
leftOf = "eDP-1"

## lists are possible on the right part of the assignment:
rightOf = ["Sony", "BenQ"]

# When multiple targets are specified, only the first connected monitor
# matching a pattern is used as the reference.

## > 2.3.2: you can also set scale, transform & rate for a given monitor
[monitors.placement.Microstep]
rate = 100
```

Try to keep the rules as simple as possible, but relatively complex scenarios are supported.

> [!note]
> Check [wlr layout UI](https://github.com/fdev31/wlr-layout-ui) which is a nice complement to configure your monitor settings.

</details>

## Commands

<PluginCommands plugin="monitors" />

## Configuration

<PluginConfig plugin="monitors" linkPrefix="config-" />

### `placement` {#config-placement}

<ConfigDefault plugin="monitors" option="placement" />

The name of the attribute must contain key words to indicate the placement type:

- `left`
- `top`
- `right`
- `bottom`

On top of this "base" placement, it can contain "alignment" information in case monitors aren't the same size:

- `start`
- `middle` | `center`
- `end`

Everything is case insensitive and extra characters will be ignored, so you can have nice to read rules so `is-on-left-end-of`, `leftend` and `LeftEndOf` design the same placement.

> [!important]
> If you don't like the screen to align on the start of the given border,
> you can use `center` (or `middle`) to center it or `end` to stick it to the opposite border.
> Eg: `topCenterOf`, `leftEndOf`, etc...

You can separate the terms with `_` to improve readability, as in `top_center_of`.

> [!important]
> At least one monitor must have **no placement rule** to serve as the anchor/reference point.
> Other monitors are positioned relative to this anchor. If all monitors have placement rules
> pointing to each other, a circular dependency occurs and the layout cannot be computed.

See [Placement Examples](#placement-examples) for visual diagrams.

#### Monitor Patterns {#monitor-patterns}

Both the monitor being configured and the target monitor can be specified using:

1. **Port name** (exact match) - e.g., `eDP-1`, `HDMI-A-1`, `DP-1`
2. **Description substring** (partial match) - e.g., `Hisense`, `BenQ`, `DELL P2417H`

The plugin first checks for an exact port name match, then searches monitor descriptions for a substring match. Descriptions typically contain the manufacturer, model, and serial number (as shown by `hyprctl monitors`).

**Examples:**

```toml
# Target by port name
[monitors.placement.Sony]
topOf = "eDP-1"

# Target by brand/model name
[monitors.placement.Hisense]
top_middle_of = "BenQ"

# Mix both approaches
[monitors.placement."DELL P2417H"]
right_end_of = "HDMI-A-1"
```

> [!tip]
> Run `hyprctl monitors` (or `nirictl outputs` for Niri) to see the full description of each connected monitor.

#### Monitor settings

Not only can you place monitors relatively to each other, but you can also set specific settings for a given monitor.

The following settings are supported:

- `scale`
- `transform`
- `rate`
- `resolution`

```toml
[monitors.placement."My monitor brand"]
leftOf = "eDP-1"
rate = 60
scale = 1.5
transform = 1 # 0: normal, 1: 90°, 2: 180°, 3: 270°, 4: flipped, 5: flipped 90°, 6: flipped 180°, 7: flipped 270°
resolution = "1920x1080"  # can also be expressed as [1920, 1080]
```

### `startup_relayout` {#config-startup-relayout}

<ConfigDefault plugin="monitors" option="startup_relayout" />

When set to `false`, do not initialize the monitor layout on startup or when configuration is reloaded.

### `relayout_on_config_change` {#config-relayout-on-config-change}

<ConfigDefault plugin="monitors" option="relayout_on_config_change" />

When set to `false`, do not relayout when Hyprland config is reloaded.

### `new_monitor_delay` {#config-new-monitor-delay}

<ConfigDefault plugin="monitors" option="new_monitor_delay" />

The layout computation happens after this delay when a new monitor is detected, to let time for things to settle.

### `hotplug_command` {#config-hotplug-command}

<ConfigDefault plugin="monitors" option="hotplug_command" />

Allows to run a command when any monitor is plugged.

```toml
[monitors]
hotplug_command = "wlrlui -m"
```

### `hotplug_commands` {#config-hotplug-commands}

<ConfigDefault plugin="monitors" option="hotplug_commands" />

Allows to run a command when a specific monitor is plugged.

Example to load a specific profile using [wlr layout ui](https://github.com/fdev31/wlr-layout-ui):

```toml
[monitors.hotplug_commands]
"DELL P2417H CJFH277Q3HCB" = "wlrlui rotated"
```

### `unknown` {#config-unknown}

<ConfigDefault plugin="monitors" option="unknown" />

Allows to run a command when no monitor layout has been changed (no rule applied).

```toml
[monitors]
unknown = "wlrlui"
```

## Placement Examples {#placement-examples}

This section provides visual diagrams to help understand monitor placement rules.

### Basic Positions

The four basic placement directions position a monitor relative to another:

#### `topOf` - Monitor above another

<img src="/images/monitors/basic-top-of.svg" alt="Monitor A placed on top of Monitor B" style="max-width: 36%" />

```toml
[monitors.placement.A]
topOf = "B"
```

#### `bottomOf` - Monitor below another

<img src="/images/monitors/basic-bottom-of.svg" alt="Monitor A placed below Monitor B" style="max-width: 36%" />

```toml
[monitors.placement.A]
bottomOf = "B"
```

#### `leftOf` - Monitor to the left

<img src="/images/monitors/basic-left-of.svg" alt="Monitor A placed to the left of Monitor B" style="max-width: 68%" />

```toml
[monitors.placement.A]
leftOf = "B"
```

#### `rightOf` - Monitor to the right

<img src="/images/monitors/basic-right-of.svg" alt="Monitor A placed to the right of Monitor B" style="max-width: 68%" />

```toml
[monitors.placement.A]
rightOf = "B"
```

### Alignment Modifiers

When monitors have different sizes, alignment modifiers control where the smaller monitor aligns along the edge.

#### Horizontal placement (`leftOf` / `rightOf`)

**Start (default)** - Top edges align:

<img src="/images/monitors/align-left-start.svg" alt="Monitor A to the left of B, top edges aligned" style="max-width: 57%" />

```toml
[monitors.placement.A]
leftOf = "B"  # same as leftStartOf
```

**Center / Middle** - Vertically centered:

<img src="/images/monitors/align-left-center.svg" alt="Monitor A to the left of B, vertically centered" style="max-width: 57%" />

```toml
[monitors.placement.A]
leftCenterOf = "B"  # or leftMiddleOf
```

**End** - Bottom edges align:

<img src="/images/monitors/align-left-end.svg" alt="Monitor A to the left of B, bottom edges aligned" style="max-width: 57%" />

```toml
[monitors.placement.A]
leftEndOf = "B"
```

#### Vertical placement (`topOf` / `bottomOf`)

**Start (default)** - Left edges align:

<img src="/images/monitors/align-top-start.svg" alt="Monitor A on top of B, left edges aligned" style="max-width: 36%" />

```toml
[monitors.placement.A]
topOf = "B"  # same as topStartOf
```

**Center / Middle** - Horizontally centered:

<img src="/images/monitors/align-top-center.svg" alt="Monitor A on top of B, horizontally centered" style="max-width: 36%" />

```toml
[monitors.placement.A]
topCenterOf = "B"  # or topMiddleOf
```

**End** - Right edges align:

<img src="/images/monitors/align-top-end.svg" alt="Monitor A on top of B, right edges aligned" style="max-width: 36%" />

```toml
[monitors.placement.A]
topEndOf = "B"
```

### Transform (Rotation)

The `transform` setting rotates or flips the monitor. Values 1 and 3 switch the monitor to portrait mode.

| Value | Rotation | Description |
|-------|----------|-------------|
| 0 | Normal | No rotation (landscape) |
| 1 | 90° | Portrait (rotated right) |
| 2 | 180° | Upside down |
| 3 | 270° | Portrait (rotated left) |
| 4 | Flipped | Mirrored horizontally |
| 5 | Flipped 90° | Mirrored + 90° |
| 6 | Flipped 180° | Mirrored + 180° |
| 7 | Flipped 270° | Mirrored + 270° |

### Common Setups

#### Dual side-by-side

<img src="/images/monitors/setup-dual.svg" alt="Dual monitor setup: A and B side by side" style="max-width: 68%" />

```toml
[monitors.placement.A]
leftOf = "B"
```

#### Triple horizontal

<img src="/images/monitors/setup-triple.svg" alt="Triple monitor setup: A, B, C in a row" style="max-width: 100%" />

```toml
[monitors.placement.A]
leftOf = "B"

[monitors.placement.C]
rightOf = "B"
```

#### Stacked (vertical)

<img src="/images/monitors/setup-stacked.svg" alt="Stacked monitor setup: A on top, B in middle, C at bottom" style="max-width: 36%" />

```toml
[monitors.placement.A]
topOf = "B"

[monitors.placement.C]
bottomOf = "B"
```

### Real-World Example: L-Shape with Portrait Monitor

This example shows a complex 3-monitor setup combining portrait mode, corner alignment, and different-sized displays.

**Layout:**

<img src="/images/monitors/real-world-l-shape.svg" alt="L-shape monitor setup with portrait monitor A, anchor B, and landscape C" style="max-width: 57%" />

Where:

- **A** (HDMI-A-1) = Portrait monitor (transform=1), directly on top of B (blue)
- **B** (eDP-1) = Main anchor monitor, landscape (green)
- **C** = Landscape monitor, positioned at the bottom-right corner of A (orange)

**Configuration:**

```toml
[monitors.placement.CJFH277Q3HCB]
top_of = "eDP-1"
transform = 1
scale = 0.83

[monitors.placement.CJFH27888CUB]
right_end_of = "HDMI-A-1"
```

**Explanation:**

1. **B (eDP-1)** has no placement rule, making it the anchor/reference point
2. **A (CJFH277Q3HCB)** is placed on top of B with `top_of = "eDP-1"`, rotated to portrait with `transform = 1`, and scaled to 83%
3. **C (CJFH27888CUB)** uses `right_end_of = "HDMI-A-1"` to position itself to the right of A with bottom edges aligned, creating the L-shape

The `right_end_of` placement is key here: it aligns C's bottom edge with A's bottom edge, tucking C into the corner rather than aligning at the top (which `rightOf` would do).
