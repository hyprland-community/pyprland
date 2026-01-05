import pytest
import colorsys
from pyprland.plugins.wallpapers import Extension
from pyprland.plugins.wallpapers.colorutils import nicify_oklab


@pytest.fixture
def wallpaper_plugin():
    return Extension("wallpapers")


def test_color_scheme_props(wallpaper_plugin):
    schemes = {
        "pastel": {
            "min_sat": 0.2,
            "max_sat": 0.5,
            "min_light": 0.6,
            "max_light": 0.9,
        },
        "fluo": {
            "min_sat": 0.7,
            "max_sat": 1.0,
            "min_light": 0.4,
            "max_light": 0.85,
        },
        "fluo_variant": {  # Test startswith("fluo")
            "min_sat": 0.7,
            "max_sat": 1.0,
            "min_light": 0.4,
            "max_light": 0.85,
        },
        "vibrant": {
            "min_sat": 0.5,
            "max_sat": 0.8,
            "min_light": 0.4,
            "max_light": 0.85,
        },
        "mellow": {
            "min_sat": 0.3,
            "max_sat": 0.5,
            "min_light": 0.4,
            "max_light": 0.85,
        },
        "neutral": {
            "min_sat": 0.05,
            "max_sat": 0.1,
            "min_light": 0.4,
            "max_light": 0.65,
        },
        "earth": {
            "min_sat": 0.2,
            "max_sat": 0.6,
            "min_light": 0.2,
            "max_light": 0.6,
        },
    }

    for scheme, expected in schemes.items():
        wallpaper_plugin.config = {"color_scheme": scheme}
        props = wallpaper_plugin._get_color_scheme_props()
        assert props == expected, f"Failed for scheme: {scheme}"


def test_color_scheme_props_default(wallpaper_plugin):
    wallpaper_plugin.config = {"color_scheme": "default"}
    props = wallpaper_plugin._get_color_scheme_props()
    assert props == {}


def test_generate_palette_basic(wallpaper_plugin):
    def mock_process_color(rgb):
        return (0.0, 0.5, 1.0)  # H=0, L=0.5, S=1.0

    rgb_list = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    wallpaper_plugin.config = {}

    palette = wallpaper_plugin._generate_palette(rgb_list, mock_process_color, theme="dark")

    assert palette["scheme"] == "dark"
    # Basic check for existence
    assert "colors.primary" in palette
    assert palette["colors.primary"].startswith("#")


def test_generate_palette_islands(wallpaper_plugin):
    # Mock return values for different inputs
    def mock_process_color(rgb):
        if rgb == (255, 0, 0):
            return (0.0, 0.5, 1.0)  # Red
        if rgb == (0, 255, 0):
            return (0.33, 0.5, 1.0)  # Green
        if rgb == (0, 0, 255):
            return (0.66, 0.5, 1.0)  # Blue
        return (0.0, 0.0, 0.0)

    rgb_list = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    wallpaper_plugin.config = {"variant": "islands"}

    palette = wallpaper_plugin._generate_palette(rgb_list, mock_process_color)

    # In islands mode:
    # Primary uses 1st color (Red hue 0.0)
    # Secondary uses 2nd color (Green hue 0.33)
    # Tertiary uses 3rd color (Blue hue 0.66)

    p_hex = palette["colors.primary"]
    s_hex = palette["colors.secondary"]
    t_hex = palette["colors.tertiary"]

    # They should be different in islands mode given different inputs
    assert p_hex != s_hex
    assert s_hex != t_hex
    assert p_hex != t_hex


def test_set_alpha(wallpaper_plugin):
    # Hex 6
    assert wallpaper_plugin._set_alpha("FFFFFF", "0.5") == "rgba(255, 255, 255, 0.5)"
    # Hex 7 (#)
    assert wallpaper_plugin._set_alpha("#FFFFFF", "0.5") == "rgba(255, 255, 255, 0.5)"
    # RGBA already
    assert wallpaper_plugin._set_alpha("rgba(0, 0, 0, 1.0)", "0.5") == "rgba(0, 0, 0, 0.5)"


def test_set_lightness(wallpaper_plugin):
    # Black -> lighter
    # #000000 is H=0, L=0, S=0. +20% lightness = L=0.2
    # Expect non-black
    res = wallpaper_plugin._set_lightness("#000000", "20")
    assert res != "#000000"

    # White -> darker
    # #FFFFFF is L=1.0. -20% = L=0.8
    res = wallpaper_plugin._set_lightness("#FFFFFF", "-20")
    assert res != "#ffffff"
    assert res != "#FFFFFF"


@pytest.mark.asyncio
async def test_apply_filters(wallpaper_plugin):
    replacements = {"color": "#FF0000"}

    # Simple replacement
    content = "Color is {{ color }}"
    res = await wallpaper_plugin._apply_filters(content, replacements)
    assert res == "Color is #FF0000"

    # Filter set_alpha
    content = "Alpha: {{ color | set_alpha: 0.5 }}"
    res = await wallpaper_plugin._apply_filters(content, replacements)
    assert "rgba(255, 0, 0, 0.5)" in res

    # Filter set_lightness
    content = "Light: {{ color | set_lightness: -50 }}"
    res = await wallpaper_plugin._apply_filters(content, replacements)
    assert res != "Light: #FF0000"

    # Unknown filter (should return value as is)
    content = "Unknown: {{ color | invalid_filter: 123 }}"
    res = await wallpaper_plugin._apply_filters(content, replacements)
    assert res == "Unknown: #FF0000"

    # Missing variable
    content = "Missing: {{ missing_var }}"
    res = await wallpaper_plugin._apply_filters(content, replacements)
    assert res == "Missing: {{ missing_var }}"


def test_color_scheme_effect_on_saturation(wallpaper_plugin):
    """Verify that color schemes actually impact the visual properties of the generated colors."""
    # Base color: Bright Red (High Saturation)
    base_rgb = (255, 0, 0)

    # 1. Neutral (Low Saturation)
    wallpaper_plugin.config = {"color_scheme": "neutral"}
    props_neutral = wallpaper_plugin._get_color_scheme_props()
    res_neutral = nicify_oklab(base_rgb, **props_neutral)

    # Convert back to HLS to check saturation (0.0 - 1.0)
    # rgb_to_hls expects 0.0-1.0 inputs
    _, l_neutral, s_neutral = colorsys.rgb_to_hls(res_neutral[0] / 255.0, res_neutral[1] / 255.0, res_neutral[2] / 255.0)

    # 2. Fluo (High Saturation)
    wallpaper_plugin.config = {"color_scheme": "fluo"}
    props_fluo = wallpaper_plugin._get_color_scheme_props()
    res_fluo = nicify_oklab(base_rgb, **props_fluo)

    _, l_fluo, s_fluo = colorsys.rgb_to_hls(res_fluo[0] / 255.0, res_fluo[1] / 255.0, res_fluo[2] / 255.0)

    # Assertions
    # Neutral saturation should be low
    # Note: Oklab chroma conversion to HLS saturation is not 1:1, so we use a lenient threshold
    # 0.33 was observed for pure red input with neutral settings
    assert s_neutral <= 0.4, f"Neutral saturation {s_neutral} is too high (expected <= 0.4)"

    # Fluo saturation should be high (min_sat is 0.7)
    assert s_fluo >= 0.6, f"Fluo saturation {s_fluo} is too low (expected >= 0.6)"

    # Confirm relative difference - this is the most important check for "greyer vs more saturated"
    assert s_neutral < s_fluo - 0.2, "Neutral scheme should be significantly less saturated than Fluo scheme"
