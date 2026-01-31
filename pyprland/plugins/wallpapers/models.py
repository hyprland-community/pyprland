"""Models for color variants and configurations."""

from dataclasses import dataclass
from enum import StrEnum

HEX_LEN = 6
HEX_LEN_HASH = 7


class Theme(StrEnum):
    """Light/dark theme for color variant selection.

    Used to determine which color variant (dark or light) to use
    as the default when generating color palettes from wallpapers.
    """

    DARK = "dark"
    LIGHT = "light"


class ColorScheme(StrEnum):
    """Color palette schemes for wallpaper theming.

    Controls saturation and lightness ranges applied to extracted colors.
    Each scheme produces a distinct mood/aesthetic.
    """

    DEFAULT = ""  # No color adjustment
    PASTEL = "pastel"  # Soft, muted colors (high lightness, low saturation)
    FLUORESCENT = "fluo"  # Bright, vivid colors (high saturation)
    VIBRANT = "vibrant"  # Rich, saturated colors
    MELLOW = "mellow"  # Subdued, gentle colors
    NEUTRAL = "neutral"  # Minimal saturation (near grayscale)
    EARTH = "earth"  # Natural, earthy tones (lower lightness)


@dataclass
class MaterialColors:
    """Holds material design color bases."""

    primary: tuple[float, float]
    secondary: tuple[float, float]
    tertiary: tuple[float, float]


@dataclass
class ColorVariant:
    """Holds dark and light variants of a color."""

    dark: tuple[int, int, int]
    light: tuple[int, int, int]


@dataclass
class VariantConfig:
    """Configuration for processing a variant."""

    name: str
    props: tuple[float | str, float, float | str, float | str]
    mat_colors: MaterialColors
    source_hls: tuple[float, float, float]
    theme: Theme
    colors: dict[str, str]


# (hue_offset, saturation_mult, light_dark_mode, light_light_mode)
MATERIAL_VARIATIONS = {
    "source": (0.0, 1.0, "source", "source"),
    "primary": (0.0, 1.0, 0.80, 0.40),
    "on_primary": (0.0, 0.2, 0.20, 1.00),
    "primary_container": (0.0, 1.0, 0.30, 0.90),
    "on_primary_container": (0.0, 1.0, 0.90, 0.10),
    "primary_fixed": (0.0, 1.0, 0.90, 0.90),
    "primary_fixed_dim": (0.0, 1.0, 0.80, 0.80),
    "on_primary_fixed": (0.0, 1.0, 0.10, 0.10),
    "on_primary_fixed_variant": (0.0, 1.0, 0.30, 0.30),
    "secondary": (-0.15, 0.8, 0.80, 0.40),
    "on_secondary": (-0.15, 0.2, 0.20, 1.00),
    "secondary_container": (-0.15, 0.8, 0.30, 0.90),
    "on_secondary_container": (-0.15, 0.8, 0.90, 0.10),
    "secondary_fixed": (0.5, 0.8, 0.90, 0.90),
    "secondary_fixed_dim": (0.5, 0.8, 0.80, 0.80),
    "on_secondary_fixed": (0.5, 0.8, 0.10, 0.10),
    "on_secondary_fixed_variant": (0.5, 0.8, 0.30, 0.30),
    "tertiary": (0.15, 0.8, 0.80, 0.40),
    "on_tertiary": (0.15, 0.2, 0.20, 1.00),
    "tertiary_container": (0.15, 0.8, 0.30, 0.90),
    "on_tertiary_container": (0.15, 0.8, 0.90, 0.10),
    "tertiary_fixed": (0.25, 0.8, 0.90, 0.90),
    "tertiary_fixed_dim": (0.25, 0.8, 0.80, 0.80),
    "on_tertiary_fixed": (0.25, 0.8, 0.10, 0.10),
    "on_tertiary_fixed_variant": (0.25, 0.8, 0.30, 0.30),
    "error": ("=0.0", 1.0, 0.80, 0.40),
    "on_error": ("=0.0", 1.0, 0.20, 1.00),
    "error_container": ("=0.0", 1.0, 0.30, 0.90),
    "on_error_container": ("=0.0", 1.0, 0.90, 0.10),
    "surface": (0.0, 0.1, 0.10, 0.98),
    "surface_bright": (0.0, 0.1, 0.12, 0.96),
    "surface_dim": (0.0, 0.1, 0.06, 0.87),
    "surface_container_lowest": (0.0, 0.1, 0.04, 1.00),
    "surface_container_low": (0.0, 0.1, 0.10, 0.96),
    "surface_container": (0.0, 0.1, 0.12, 0.94),
    "surface_container_high": (0.0, 0.1, 0.17, 0.92),
    "surface_container_highest": (0.0, 0.1, 0.22, 0.90),
    "on_surface": (0.0, 0.1, 0.90, 0.10),
    "surface_variant": (0.0, 0.1, 0.30, 0.90),
    "on_surface_variant": (0.0, 0.1, 0.80, 0.30),
    "background": (0.0, 0.1, 0.05, 0.99),
    "on_background": (0.0, 0.1, 0.90, 0.10),
    "outline": (0.0, 0.1, 0.60, 0.50),
    "outline_variant": (0.0, 0.1, 0.30, 0.80),
    "inverse_primary": (0.0, 1.0, 0.40, 0.80),
    "inverse_surface": (0.0, 0.1, 0.90, 0.20),
    "inverse_on_surface": (0.0, 0.1, 0.20, 0.95),
    "surface_tint": (0.0, 1.0, 0.80, 0.40),
    "scrim": (0.0, 0.0, 0.0, 0.0),
    "shadow": (0.0, 0.0, 0.0, 0.0),
    "white": (0.0, 0.0, 0.99, 0.99),
    "red": ("=0.0", 1.0, 0.80, 0.40),
    "green": ("=0.333", 1.0, 0.80, 0.40),
    "yellow": ("=0.166", 1.0, 0.80, 0.40),
    "blue": ("=0.666", 1.0, 0.80, 0.40),
    "magenta": ("=0.833", 1.0, 0.80, 0.40),
    "cyan": ("=0.5", 1.0, 0.80, 0.40),
}
