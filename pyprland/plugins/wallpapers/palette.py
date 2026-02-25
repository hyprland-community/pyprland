"""Palette display utilities for wallpapers plugin."""

import colorsys
import json

from .models import Theme
from .theme import generate_palette

# Category definitions for organizing palette output
# Order matters for display - checked in sequence, first match wins
PALETTE_CATEGORIES = [
    ("primary", lambda k: "primary" in k),
    ("secondary", lambda k: "secondary" in k),
    ("tertiary", lambda k: "tertiary" in k),
    ("surface", lambda k: "surface" in k),
    ("error", lambda k: "error" in k),
    ("ansi", lambda k: any(c in k for c in ["red", "green", "yellow", "blue", "magenta", "cyan", "white"])),
    ("utility", lambda _k: True),  # Fallback for background, outline, inverse, scrim, shadow
]

# Display names for categories
CATEGORY_DISPLAY_NAMES = {
    "primary": "Primary",
    "secondary": "Secondary",
    "tertiary": "Tertiary",
    "surface": "Surface",
    "error": "Error",
    "ansi": "ANSI Colors",
    "utility": "Utility",
}


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color to RGB tuple.

    Args:
        hex_color: Hex color string with or without '#' prefix

    Returns:
        Tuple of (red, green, blue) integers 0-255
    """
    color = hex_color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def _categorize_palette(palette: dict[str, str]) -> dict[str, list[str]]:
    """Organize palette keys into categories.

    Args:
        palette: Palette dictionary from generate_palette()

    Returns:
        Dictionary mapping category names to lists of palette keys
    """
    categories: dict[str, list[str]] = {name: [] for name, _ in PALETTE_CATEGORIES}

    for key in palette:
        if key in ("scheme", "image") or not key.startswith("colors."):
            continue
        for cat_name, matcher in PALETTE_CATEGORIES:
            if matcher(key):
                categories[cat_name].append(key)
                break

    # Sort within each category
    for cat in categories.values():
        cat.sort()

    return categories


def palette_to_json(palette: dict[str, str]) -> str:
    """Convert palette to JSON format with categories and filter examples.

    Args:
        palette: Palette dictionary from generate_palette()

    Returns:
        JSON string with variables, categories, and filter documentation
    """
    categories = _categorize_palette(palette)

    output = {
        "variables": {k: v for k, v in palette.items() if k not in ("scheme", "image")},
        "categories": categories,
        "filters": {
            "set_alpha": {
                "description": "Add transparency to a color",
                "example": "{{ colors.primary.default.hex | set_alpha: 0.5 }}",
                "result": "rgba(R, G, B, 0.5)",
            },
            "set_lightness": {
                "description": "Adjust color brightness (percentage, can be negative)",
                "example": "{{ colors.primary.default.hex | set_lightness: -20 }}",
                "result": "#XXXXXX (darker)",
            },
        },
        "theme": palette.get("scheme", "dark"),
    }

    return json.dumps(output, indent=2)


def palette_to_terminal(palette: dict[str, str]) -> str:  # pylint: disable=too-many-locals
    """Convert palette to terminal-formatted output with ANSI color swatches.

    Args:
        palette: Palette dictionary from generate_palette()

    Returns:
        Formatted string with ANSI color codes for terminal display
    """
    lines = []
    categories = _categorize_palette(palette)

    # Display in order defined by PALETTE_CATEGORIES
    lines.append("   variable name prefix              |    dark mode  |  light mode")
    lines.append("-------------------------------------+---------------+--------------")
    for cat_name, _ in PALETTE_CATEGORIES:
        items = categories.get(cat_name, [])
        # Only show .dark.hex variants as base entries (skip .default, .rgb, .rgba, .hex_stripped)
        dark_items = [k for k in items if k.endswith(".dark.hex")]
        if not dark_items:
            continue

        display_name = CATEGORY_DISPLAY_NAMES.get(cat_name, cat_name.title())
        lines.append(f"\n{display_name}:")

        for dark_key in dark_items:
            # Get dark color
            dark_value = palette[dark_key]
            r_dark, g_dark, b_dark = hex_to_rgb(dark_value)
            dark_swatch = f"\033[48;2;{r_dark};{g_dark};{b_dark}m    \033[0m"

            # Derive light key and get light color
            light_key = dark_key.replace(".dark.hex", ".light.hex")
            light_value = palette.get(light_key, "")
            if light_value:
                r_light, g_light, b_light = hex_to_rgb(light_value)
                light_swatch = f"\033[48;2;{r_light};{g_light};{b_light}m    \033[0m"
                light_part = f"{light_swatch} {light_value}"
            else:
                light_part = ""

            # Two-column layout: dark | light
            lines.append(f"   {dark_key[:-9]:<35} {dark_swatch} {dark_value}  |  {light_part}")

    # Add filter examples
    lines.append("\nFilters:")
    lines.append("  set_alpha     {{ colors.primary.dark.hex | set_alpha: 0.5 }}")
    lines.append("  set_lightness {{ colors.primary.dark.hex | set_lightness: -20 }}")

    return "\n".join(lines)


def generate_sample_palette(
    base_rgb: tuple[int, int, int],
    theme: Theme = Theme.DARK,
) -> dict[str, str]:
    """Generate a sample palette from an RGB color.

    Args:
        base_rgb: Base color as RGB tuple (0-255 for each component)
        theme: Theme to use (Theme.DARK or Theme.LIGHT)

    Returns:
        Palette dictionary with all color variables
    """
    dominant_colors = [base_rgb] * 3

    def process_color(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
        return colorsys.rgb_to_hls(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)

    return generate_palette(dominant_colors, theme=theme, process_color=process_color)
