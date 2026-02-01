---
---

# Wallpaper Templates

The templates feature provides automatic theming for your desktop applications. When the wallpaper changes, pyprland:

1. Extracts dominant colors from the wallpaper image
2. Generates a Material Design-inspired color palette
3. Processes your template files, replacing color placeholders with actual values
4. Runs optional `post_hook` commands to apply the changes

This creates a unified color scheme across your terminal, window borders, GTK apps, and other tools - all derived from your wallpaper.

> [!tip]
> If you're migrating from *matugen* or *pywal*, your existing templates should work with minimal changes.

## Commands

| Command | Description |
|---------|-------------|
| `color <#RRGGBB> [scheme]` | Generate color palette from hex color. |
| `palette [color] [json]` | Show available color template variables. |


### Using the `color` command {#command-color}

The `color` command allows testing the palette with a specific color instead of extracting from the wallpaper:

- `pypr color "#ff0000"` - Re-generate the templates with the given color
- `pypr color "#ff0000" neutral` - Re-generate the templates with the given color and [color scheme](#config-color-scheme) (color filter)

### Using the `palette` command {#command-palette}

The `palette` command shows available color template variables:

- `pypr palette` - Show palette using colors from current wallpaper
- `pypr palette "#ff0000"` - Show palette for a specific color
- `pypr palette json` - Output palette in JSON format

## Configuration

| Option | Description |
|--------|-------------|
| `color_scheme` · *str* | Color scheme for palette generation (options: `pastel` \| `fluo` \| `vibrant` \| `mellow` \| `neutral` \| `earth` \| `fluorescent`) |
| `variant` · *str* | Color variant type for palette |
| `templates` · *dict* | Template files for color palette generation |


### `templates` *dict* {#config-templates}

Enables automatic theming by generating config files from templates using colors extracted from the wallpaper.

```toml
[wallpapers.templates.hyprland]
input_path = "~/color_configs/hyprlandcolors.sh"
output_path = "/tmp/hyprlandcolors.sh"
post_hook = "sh /tmp/hyprlandcolors.sh"
```

> [!tip]
> Mostly compatible with *matugen* template syntax.

### `color_scheme` *str* {#config-color-scheme}

Optional modification of the base color used in the templates. One of:

- **pastel** - a bit more washed colors
- **fluo** or **fluorescent** - for high color saturation
- **neutral** - for low color saturation
- **earth** - a bit more dark, a bit less blue
- **vibrant** - for moderate to high saturation
- **mellow** - for lower saturation

### `variant` *str* {#config-variant}

Changes the algorithm used to pick the primary, secondary and tertiary colors.

- **islands** - uses the 3 most popular colors from the wallpaper image

By default it will pick the "main" color and shift the hue to get the secondary and tertiary colors.

## Template Configuration

Each template requires an `input_path` (template file with placeholders) and `output_path` (where to write the result):

```toml
[wallpapers.templates.hyprland]
input_path = "~/color_configs/hyprlandcolors.sh"
output_path = "/tmp/hyprlandcolors.sh"
post_hook = "sh /tmp/hyprlandcolors.sh"  # optional: runs after this template
```

| Option | Required | Description |
|--------|----------|-------------|
| `input_path` | Yes | Path to template file containing <code v-pre>{{placeholders}}</code> |
| `output_path` | Yes | Where to write the processed output |
| `post_hook` | No | Command to run after this specific template is generated |

> [!note]
> **`post_hook` vs `post_command`**: The `post_hook` runs after each individual template is generated. The global [`post_command`](./wallpapers#config-post-command) runs once after the wallpaper is set and all templates are processed.

## Template Syntax

Use double curly braces to insert color values:

```txt
{{colors.<color_name>.<variant>.<format>}}
```

| Part | Options | Description |
|------|---------|-------------|
| `color_name` | See [color reference](#color-reference) | The color role (e.g., `primary`, `surface`) |
| `variant` | `default`, `dark`, `light` | Which theme variant to use |
| `format` | `hex`, `hex_stripped`, `rgb`, `rgba` | Output format |

**Examples:**
```txt
{{colors.primary.default.hex}}           → #6495ED
{{colors.primary.default.hex_stripped}}  → 6495ED
{{colors.primary.dark.rgb}}              → rgb(100, 149, 237)
{{colors.surface.light.rgba}}            → rgba(250, 248, 245, 1.0)
```

**Shorthand:** <code v-pre>{{colors.primary.default}}</code> is equivalent to <code v-pre>{{colors.primary.default.hex}}</code>

The `default` variant automatically selects `dark` or `light` based on [theme detection](#theme-detection).

## Special Variables

In addition to colors, these variables are available in templates:

| Variable | Description | Example Value |
|----------|-------------|---------------|
| <code v-pre>{{image}}</code> | Full path to the current wallpaper | `/home/user/Pictures/sunset.jpg` |
| <code v-pre>{{scheme}}</code> | Detected theme | `dark` or `light` |

## Color Formats

| Format | Example | Typical Use |
|--------|---------|-------------|
| `hex` | `#6495ED` | Most applications, CSS |
| `hex_stripped` | `6495ED` | Hyprland configs, apps that don't want `#` |
| `rgb` | `rgb(100, 149, 237)` | CSS, GTK |
| `rgba` | `rgba(100, 149, 237, 1.0)` | CSS with opacity |

## Filters

Filters modify color values. Use the pipe (`|`) syntax:

```txt
{{colors.primary.default.hex | filter_name: argument}}
```

**`set_alpha`** - Add transparency to a color

Converts the color to RGBA format with the specified alpha value (0.0 to 1.0):

```txt
Template:  {{colors.primary.default.hex | set_alpha: 0.5}}
Output:    rgba(100, 149, 237, 0.5)

Template:  {{colors.surface.default.hex | set_alpha: 0.8}}
Output:    rgba(26, 22, 18, 0.8)
```

**`set_lightness`** - Adjust color brightness

Changes the lightness by a percentage (-100 to 100). Positive values lighten, negative values darken:

```txt
Template:  {{colors.primary.default.hex | set_lightness: 20}}
Output:    #8AB4F8  (20% lighter)

Template:  {{colors.primary.default.hex | set_lightness: -20}}
Output:    #3A5980  (20% darker)
```

## Theme Detection {#theme-detection}

The `default` color variant automatically adapts to your system theme. Detection order:

1. **gsettings** (GNOME/GTK): `gsettings get org.gnome.desktop.interface color-scheme`
2. **darkman**: `darkman get`
3. **Fallback**: defaults to `dark` if neither is available

You can check the detected theme using the <code v-pre>{{scheme}}</code> variable in your templates.

## Color Reference {#color-reference}

Colors follow the Material Design 3 color system, organized by role:

**Primary Colors** - Main accent color derived from the wallpaper

| Color | Description |
|-------|-------------|
| `primary` | Main accent color |
| `on_primary` | Text/icons displayed on primary color |
| `primary_container` | Less prominent container using primary hue |
| `on_primary_container` | Text/icons on primary container |
| `primary_fixed` | Fixed primary that doesn't change with theme |
| `primary_fixed_dim` | Dimmer variant of fixed primary |
| `on_primary_fixed` | Text on fixed primary |
| `on_primary_fixed_variant` | Variant text on fixed primary |

**Secondary Colors** - Complementary accent (hue-shifted from primary)

| Color | Description |
|-------|-------------|
| `secondary` | Secondary accent color |
| `on_secondary` | Text/icons on secondary |
| `secondary_container` | Container using secondary hue |
| `on_secondary_container` | Text on secondary container |
| `secondary_fixed`, `secondary_fixed_dim` | Fixed variants |
| `on_secondary_fixed`, `on_secondary_fixed_variant` | Text on fixed |

**Tertiary Colors** - Additional accent (hue-shifted opposite of secondary)

| Color | Description |
|-------|-------------|
| `tertiary` | Tertiary accent color |
| `on_tertiary` | Text/icons on tertiary |
| `tertiary_container` | Container using tertiary hue |
| `on_tertiary_container` | Text on tertiary container |
| `tertiary_fixed`, `tertiary_fixed_dim` | Fixed variants |
| `on_tertiary_fixed`, `on_tertiary_fixed_variant` | Text on fixed |

**Surface Colors** - Backgrounds and containers

| Color | Description |
|-------|-------------|
| `surface` | Default background |
| `surface_bright` | Brighter surface variant |
| `surface_dim` | Dimmer surface variant |
| `surface_container_lowest` | Lowest emphasis container |
| `surface_container_low` | Low emphasis container |
| `surface_container` | Default container |
| `surface_container_high` | High emphasis container |
| `surface_container_highest` | Highest emphasis container |
| `on_surface` | Text/icons on surface |
| `surface_variant` | Alternative surface |
| `on_surface_variant` | Text on surface variant |
| `background` | App background |
| `on_background` | Text on background |

**Error Colors** - Error states and alerts

| Color | Description |
|-------|-------------|
| `error` | Error color (red hue) |
| `on_error` | Text on error |
| `error_container` | Error container background |
| `on_error_container` | Text on error container |

**Utility Colors**

| Color | Description |
|-------|-------------|
| `source` | Original extracted color (unmodified) |
| `outline` | Borders and dividers |
| `outline_variant` | Subtle borders |
| `inverse_primary` | Primary for inverse surfaces |
| `inverse_surface` | Inverse surface color |
| `inverse_on_surface` | Text on inverse surface |
| `surface_tint` | Tint overlay for elevation |
| `scrim` | Overlay for modals/dialogs |
| `shadow` | Shadow color |
| `white` | Pure white |

**ANSI Terminal Colors** - Standard terminal color palette

| Color | Description |
|-------|-------------|
| `red` | ANSI red |
| `green` | ANSI green |
| `yellow` | ANSI yellow |
| `blue` | ANSI blue |
| `magenta` | ANSI magenta |
| `cyan` | ANSI cyan |

## Examples

**Hyprland Window Borders**

Config (`pyprland.toml`):
```toml
[wallpapers.templates.hyprland]
input_path = "~/color_configs/hyprlandcolors.sh"
output_path = "/tmp/hyprlandcolors.sh"
post_hook = "sh /tmp/hyprlandcolors.sh"
```

Template (`~/color_configs/hyprlandcolors.sh`):
```txt
hyprctl keyword general:col.active_border "rgb({{colors.primary.default.hex_stripped}}) rgb({{colors.tertiary.default.hex_stripped}}) 30deg"
hyprctl keyword general:col.inactive_border "rgb({{colors.surface_variant.default.hex_stripped}})"
hyprctl keyword decoration:shadow:color "rgba({{colors.shadow.default.hex_stripped}}ee)"
```

Output (after processing with a blue-toned wallpaper):
```sh
hyprctl keyword general:col.active_border "rgb(6495ED) rgb(ED6495) 30deg"
hyprctl keyword general:col.inactive_border "rgb(3D3D3D)"
hyprctl keyword decoration:shadow:color "rgba(000000ee)"
```

**Kitty Terminal Theme**

Config:
```toml
[wallpapers.templates.kitty]
input_path = "~/color_configs/kitty_theme.conf"
output_path = "~/.config/kitty/current-theme.conf"
post_hook = "kill -SIGUSR1 $(pgrep kitty) 2>/dev/null || true"
```

Template (`~/color_configs/kitty_theme.conf`):
```sh
# Auto-generated theme from wallpaper: {{image}}
# Scheme: {{scheme}}

foreground {{colors.on_background.default.hex}}
background {{colors.background.default.hex}}
cursor {{colors.primary.default.hex}}
cursor_text_color {{colors.on_primary.default.hex}}
selection_foreground {{colors.on_primary.default.hex}}
selection_background {{colors.primary.default.hex}}

# ANSI colors
color0 {{colors.surface.default.hex}}
color1 {{colors.red.default.hex}}
color2 {{colors.green.default.hex}}
color3 {{colors.yellow.default.hex}}
color4 {{colors.blue.default.hex}}
color5 {{colors.magenta.default.hex}}
color6 {{colors.cyan.default.hex}}
color7 {{colors.on_surface.default.hex}}
```

**GTK4 CSS Theme**

Config:
```toml
[wallpapers.templates.gtk4]
input_path = "~/color_configs/gtk.css"
output_path = "~/.config/gtk-4.0/colors.css"
```

Template:
```css
/* Auto-generated from wallpaper */
@define-color accent_bg_color {{colors.primary.default.hex}};
@define-color accent_fg_color {{colors.on_primary.default.hex}};
@define-color window_bg_color {{colors.surface.default.hex}};
@define-color window_fg_color {{colors.on_surface.default.hex}};
@define-color headerbar_bg_color {{colors.surface_container.default.hex}};
@define-color card_bg_color {{colors.surface_container_low.default.hex}};
@define-color view_bg_color {{colors.background.default.hex}};
@define-color popover_bg_color {{colors.surface_container_high.default.hex}};

/* With transparency */
@define-color sidebar_bg_color {{colors.surface_container.default.hex | set_alpha: 0.95}};
```

**JSON Export (for external tools)**

Config:
```toml
[wallpapers.templates.json]
input_path = "~/color_configs/colors.json"
output_path = "~/.cache/current-colors.json"
post_hook = "notify-send 'Theme Updated' 'New colors from wallpaper'"
```

Template:
```json
{
  "scheme": "{{scheme}}",
  "wallpaper": "{{image}}",
  "colors": {
    "primary": "{{colors.primary.default.hex}}",
    "secondary": "{{colors.secondary.default.hex}}",
    "tertiary": "{{colors.tertiary.default.hex}}",
    "background": "{{colors.background.default.hex}}",
    "surface": "{{colors.surface.default.hex}}",
    "error": "{{colors.error.default.hex}}"
  }
}
```

## Troubleshooting

For general pyprland issues, see the [Troubleshooting](./Troubleshooting) page.

**Template not updating?**
- Verify `input_path` exists and is readable
- Check pyprland logs:
  - **Systemd**: `journalctl --user -u pyprland -f`
  - **exec-once**: Check your log file (e.g., `tail -f ~/pypr.log`)
- Enable debug logging with `--debug` or `--debug <logfile>` (see [Getting Started](./Getting-started#running-the-daemon))
- Ensure the wallpapers plugin is loaded in your config

**Colors look wrong or washed out?**
- Try different [`color_scheme`](#config-color-scheme) values: `vibrant`, `pastel`, `fluo`
- Use [`variant = "islands"`](#config-variant) to pick colors from different areas of the image

**Theme detection not working?**
- Install `darkman` or ensure gsettings is available
- Force a theme by using `.dark` or `.light` variants instead of `.default`

**`post_hook` not running?**
- Commands run asynchronously; check for errors in logs
- Ensure the command is valid and executable
- Enable debug logging to see command execution details
