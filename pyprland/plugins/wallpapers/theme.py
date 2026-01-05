"""Theme detection and palette generation logic."""

import asyncio
import colorsys
import logging
from collections.abc import Callable
from typing import cast

from .imageutils import (
    get_variant_color,
    to_hex,
    to_rgb,
    to_rgba,
)
from .models import MATERIAL_VARIATIONS, ColorVariant, MaterialColors, VariantConfig


async def detect_theme() -> str:
    """Detect the system theme (light/dark)."""
    # Try gsettings (GNOME/GTK)
    try:
        proc = await asyncio.create_subprocess_shell(
            "gsettings get org.gnome.desktop.interface color-scheme",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            output = stdout.decode().strip().lower()
            if "prefer-light" in output or "'light'" in output:
                return "light"
            if "prefer-dark" in output or "'dark'" in output:
                return "dark"
    except Exception:  # pylint: disable=broad-exception-caught
        logging.getLogger(__name__).debug("gsettings not available for theme detection")

    # Try darkman
    try:
        proc = await asyncio.create_subprocess_shell(
            "darkman get",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            return stdout.decode().strip()
    except Exception:  # pylint: disable=broad-exception-caught
        logging.getLogger(__name__).debug("darkman not available for theme detection")

    return "dark"


def get_color_scheme_props(color_scheme: str) -> dict[str, float]:
    """Return color scheme properties suitable for nicify_oklab.

    Args:
        color_scheme: The name of the color scheme (e.g. "pastel", "vibrant")
    """
    oklab_args: dict[str, float] = {}
    scheme = color_scheme.lower()

    if scheme == "pastel":
        oklab_args = {
            "min_sat": 0.2,
            "max_sat": 0.5,
            "min_light": 0.6,
            "max_light": 0.9,
        }
    elif scheme.startswith("fluo"):
        oklab_args = {
            "min_sat": 0.7,
            "max_sat": 1.0,
            "min_light": 0.4,
            "max_light": 0.85,
        }
    elif scheme == "vibrant":
        oklab_args = {
            "min_sat": 0.5,
            "max_sat": 0.8,
            "min_light": 0.4,
            "max_light": 0.85,
        }
    elif scheme == "mellow":
        oklab_args = {
            "min_sat": 0.3,
            "max_sat": 0.5,
            "min_light": 0.4,
            "max_light": 0.85,
        }
    elif scheme == "neutral":
        oklab_args = {
            "min_sat": 0.05,
            "max_sat": 0.1,
            "min_light": 0.4,
            "max_light": 0.65,
        }
    elif scheme == "earth":
        oklab_args = {
            "min_sat": 0.2,
            "max_sat": 0.6,
            "min_light": 0.2,
            "max_light": 0.6,
        }
    return oklab_args


def _get_rgb_for_variant(
    l_val: str | float,
    cur_h: float,
    cur_s: float,
    source_hls: tuple[float, float, float],
) -> tuple[int, int, int]:
    """Get RGB color for a specific variant (lightness).

    Args:
        l_val: Lightness value or "source" to use source color
        cur_h: Current hue
        cur_s: Current saturation
        source_hls: Source color in HLS format
    """
    if l_val == "source":
        r, g, b = colorsys.hls_to_rgb(*source_hls)
        return int(r * 255), int(g * 255), int(b * 255)
    return get_variant_color(cur_h, cur_s, float(l_val))


def _get_base_hs(
    name: str,
    mat_colors: MaterialColors,
    h_off: float | str,
    variant_type: str | None = None,
) -> tuple[float, float, float | str]:
    """Determine base hue, saturation and offset for a color rule.

    Args:
        name: Name of the color rule
        mat_colors: Material colors configuration
        h_off: Hue offset
        variant_type: Type of variant (e.g. "islands")
    """
    used_h, used_s = mat_colors.primary
    used_off = h_off

    if variant_type == "islands":
        if "secondary" in name and "fixed" not in name:
            used_h, used_s = mat_colors.secondary
            used_off = 0.0
        elif "tertiary" in name and "fixed" not in name:
            used_h, used_s = mat_colors.tertiary
            used_off = 0.0
    return used_h, used_s, used_off


def _populate_colors(
    colors: dict[str, str],
    name: str,
    theme: str,
    variant: ColorVariant,
) -> None:
    """Populate the colors dict with dark, light and default variants.

    Args:
        colors: Dictionary to populate with color values
        name: Name of the color variant
        theme: Current theme ("dark" or "light")
        variant: ColorVariant object containing dark and light RGB values
    """
    r_dark, g_dark, b_dark = variant.dark
    r_light, g_light, b_light = variant.light

    # Dark variants
    colors[f"colors.{name}.dark"] = to_hex(r_dark, g_dark, b_dark)
    colors[f"colors.{name}.dark.hex"] = to_hex(r_dark, g_dark, b_dark)
    colors[f"colors.{name}.dark.hex_stripped"] = to_hex(r_dark, g_dark, b_dark)[1:]
    colors[f"colors.{name}.dark.rgb"] = to_rgb(r_dark, g_dark, b_dark)
    colors[f"colors.{name}.dark.rgba"] = to_rgba(r_dark, g_dark, b_dark)

    # Light variants
    colors[f"colors.{name}.light"] = to_hex(r_light, g_light, b_light)
    colors[f"colors.{name}.light.hex"] = to_hex(r_light, g_light, b_light)
    colors[f"colors.{name}.light.hex_stripped"] = to_hex(r_light, g_light, b_light)[1:]
    colors[f"colors.{name}.light.rgb"] = to_rgb(r_light, g_light, b_light)
    colors[f"colors.{name}.light.rgba"] = to_rgba(r_light, g_light, b_light)

    # Default (chosen)
    if theme == "dark":
        r_chosen, g_chosen, b_chosen = r_dark, g_dark, b_dark
    else:
        r_chosen, g_chosen, b_chosen = r_light, g_light, b_light

    chosen_hex = to_hex(r_chosen, g_chosen, b_chosen)
    colors[f"colors.{name}"] = chosen_hex
    colors[f"colors.{name}.default.hex"] = chosen_hex
    colors[f"colors.{name}.default.hex_stripped"] = chosen_hex[1:]
    colors[f"colors.{name}.default.rgb"] = to_rgb(r_chosen, g_chosen, b_chosen)
    colors[f"colors.{name}.default.rgba"] = to_rgba(r_chosen, g_chosen, b_chosen)


def _process_material_variant(
    config: VariantConfig,
    variant_type: str | None = None,
) -> None:
    """Process a single material variant and populate colors.

    Args:
        config: Configuration for the variant
        variant_type: Type of variant (optional)
    """
    h_off, s_mult, l_dark, l_light = config.props
    used_h, used_s, used_off = _get_base_hs(config.name, config.mat_colors, cast("float | str", h_off), variant_type)

    cur_h = float(used_off[1:]) if isinstance(used_off, str) and used_off.startswith("=") else (used_h + float(used_off)) % 1.0
    cur_s = max(0.0, min(1.0, used_s * s_mult))

    rgb_dark = _get_rgb_for_variant(cast("float | str", l_dark), cur_h, cur_s, config.source_hls)
    rgb_light = _get_rgb_for_variant(cast("float | str", l_light), cur_h, cur_s, config.source_hls)

    _populate_colors(
        config.colors,
        config.name,
        config.theme,
        ColorVariant(
            dark=rgb_dark,
            light=rgb_light,
        ),
    )


def generate_palette(
    rgb_list: list[tuple[int, int, int]],
    process_color: Callable[[tuple[int, int, int]], tuple[float, float, float]],
    theme: str = "dark",
    variant_type: str | None = None,
) -> dict[str, str]:
    """Generate a material-like palette from a single color.

    Args:
        rgb_list: List of RGB colors to use as base
        process_color: Function to process/nicify colors
        theme: Target theme ("dark" or "light")
        variant_type: Variant type (optional)
    """
    hue, light, sat = process_color(rgb_list[0])

    if variant_type == "islands":
        h_sec, _, s_sec = process_color(rgb_list[1])
        h_tert, _, s_tert = process_color(rgb_list[2])
    else:
        h_sec, s_sec = hue, sat
        h_tert, s_tert = hue, sat

    colors = {"scheme": theme}
    mat_colors = MaterialColors(primary=(hue, sat), secondary=(h_sec, s_sec), tertiary=(h_tert, s_tert))

    for name, props in MATERIAL_VARIATIONS.items():
        _process_material_variant(
            VariantConfig(
                name=name,
                props=cast("tuple[float | str, float, float | str, float | str]", props),
                mat_colors=mat_colors,
                source_hls=(hue, light, sat),
                theme=theme,
                colors=colors,
            ),
            variant_type,
        )

    return colors
