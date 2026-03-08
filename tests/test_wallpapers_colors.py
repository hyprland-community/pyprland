import pytest
import math
from unittest.mock import Mock, patch, MagicMock
from pyprland.plugins.wallpapers.colorutils import (
    _build_hue_histogram,
    _smooth_histogram,
    _find_peaks,
    _get_best_pixel_for_hue,
    _calculate_hue_diff,
    _select_colors_from_peaks,
    get_dominant_colors,
    nicify_oklab,
    HUE_MAX,
    MIN_SATURATION,
    MIN_BRIGHTNESS,
)
import colorsys
from pyprland.plugins.wallpapers import Extension
from pyprland.plugins.wallpapers.models import Theme
from pyprland.plugins.wallpapers.theme import (
    get_color_scheme_props,
    generate_palette,
)
from pyprland.plugins.wallpapers.templates import (
    _set_alpha,
    _set_lightness,
    _apply_filters,
)

# --- Histogram Tests ---


def test_build_hue_histogram():
    # Setup simple pixels:
    # 1. Valid: H=10, S=100, V=100
    # 2. Invalid: Low saturation
    # 3. Invalid: Low brightness
    pixels = [(10, 100, 100), (20, MIN_SATURATION - 1, 100), (30, 100, MIN_BRIGHTNESS - 1)]

    weights, indices = _build_hue_histogram(pixels)

    assert len(weights) == HUE_MAX
    assert len(indices) == HUE_MAX

    # Check valid pixel
    expected_weight = (100 * 100) / (255.0 * 255.0)
    assert math.isclose(weights[10], expected_weight, rel_tol=1e-5)
    assert indices[10] == [0]

    # Check invalid pixels
    assert weights[20] == 0.0
    assert indices[20] == []
    assert weights[30] == 0.0
    assert indices[30] == []


def test_smooth_histogram():
    weights = [0.0] * HUE_MAX
    # Single spike
    weights[10] = 16.0

    smoothed = _smooth_histogram(weights)

    # Kernel: [1, 4, 6, 4, 1] / 16
    # So index 10 (center) should receive 16 * 6/16 = 6
    assert smoothed[10] == 6.0
    # Index 9: 16 * 4/16 = 4
    assert smoothed[9] == 4.0
    # Index 11: 16 * 4/16 = 4
    assert smoothed[11] == 4.0

    # Check wrap around
    weights_wrap = [0.0] * HUE_MAX
    weights_wrap[0] = 16.0
    smoothed_wrap = _smooth_histogram(weights_wrap)
    assert smoothed_wrap[0] == 6.0
    assert smoothed_wrap[HUE_MAX - 1] == 4.0


def test_find_peaks():
    weights = [0.0] * HUE_MAX
    weights[10] = 5.0  # Peak
    weights[9] = 2.0
    weights[11] = 2.0

    weights[50] = 10.0  # Higher Peak
    weights[49] = 8.0
    weights[51] = 8.0

    peaks = _find_peaks(weights)

    # Should be sorted by value descending
    assert len(peaks) == 2
    assert peaks[0] == (10.0, 50)
    assert peaks[1] == (5.0, 10)


def test_calculate_hue_diff():
    # Direct distance
    assert _calculate_hue_diff(10, 20) == 10
    # Wrap around distance
    assert _calculate_hue_diff(10, 250) == 16  # 256 - 250 + 10 = 6 + 10 = 16 (assuming HUE_MAX 256)

    # Test specific threshold logic
    # HUE_DIFF_THRESHOLD is 128
    assert _calculate_hue_diff(0, 128) == 128
    assert _calculate_hue_diff(0, 129) == 127  # 256 - 129 = 127


# --- Color Selection Tests ---


def test_get_best_pixel_for_hue():
    target_hue = 10
    indices = [[] for _ in range(HUE_MAX)]
    indices[10] = [0, 1]

    # px0: S=50, V=50 -> w=2500
    # px1: S=100, V=100 -> w=10000 (Best)
    hsv_pixels = [(10, 50, 50), (10, 100, 100)]
    rgb_pixels = [(50, 50, 50), (100, 100, 100)]

    result = _get_best_pixel_for_hue(target_hue, indices, hsv_pixels, rgb_pixels)
    assert result == (100, 100, 100)

    # Test neighbor lookup
    indices[10] = []
    indices[11] = [0]  # Neighbor
    hsv_pixels = [(11, 50, 50)]
    rgb_pixels = [(50, 50, 50)]

    result = _get_best_pixel_for_hue(target_hue, indices, hsv_pixels, rgb_pixels)
    assert result == (50, 50, 50)


def test_select_colors_from_peaks():
    # Prepare dummy data
    peaks = [(1.0, 10), (0.8, 40), (0.5, 70)]  # All far enough apart (>21)
    indices = [[] for _ in range(HUE_MAX)]
    # Populate indices for the peak hues
    indices[10] = [0]
    indices[40] = [1]
    indices[70] = [2]

    hsv_pixels = [(10, 100, 100), (40, 100, 100), (70, 100, 100)]
    rgb_pixels = [(10, 10, 10), (40, 40, 40), (70, 70, 70)]

    colors = _select_colors_from_peaks(peaks, indices, hsv_pixels, rgb_pixels)

    assert len(colors) == 3
    assert colors[0] == (10, 10, 10)
    assert colors[1] == (40, 40, 40)
    assert colors[2] == (70, 70, 70)


def test_get_dominant_colors_integration():
    with patch("pyprland.plugins.wallpapers.colorutils.Image") as MockImage:
        # Mock Image.open context manager
        mock_img = Mock()
        MockImage.open.return_value.__enter__.return_value = mock_img

        # Mock conversions
        mock_rgb = Mock()
        mock_rgb.getdata.return_value = [(255, 0, 0)] * 10

        mock_hsv = Mock()
        mock_hsv.getdata.return_value = [(0, 100, 100)] * 10  # Red pixels

        # Need to handle chaining: img.convert("RGB") -> mock_rgb, mock_rgb.convert("HSV") -> mock_hsv
        # And img.thumbnail

        def convert_side_effect(mode):
            if mode == "RGB":
                return mock_rgb
            if mode == "HSV":
                return mock_hsv
            return Mock()

        mock_img.convert.side_effect = convert_side_effect
        mock_rgb.convert.side_effect = convert_side_effect

        colors = get_dominant_colors("dummy.jpg")

        assert len(colors) == 3
        # Should be mostly red
        assert colors[0] == (255, 0, 0)
        # Should be padded
        assert colors[1] == (255, 0, 0)


# --- OkLab Tests ---


def test_nicify_oklab():
    # Black
    res = nicify_oklab((0, 0, 0))
    # It will brighten it due to min_light constraint
    assert res != (0, 0, 0)
    assert res[0] > 0

    # White
    res = nicify_oklab((255, 255, 255))
    # It might darken it due to max_light
    assert res != (255, 255, 255)

    # Simple roundtrip stability check (values shouldn't explode)
    test_color = (100, 150, 200)
    res = nicify_oklab(test_color)
    assert 0 <= res[0] <= 255
    assert 0 <= res[1] <= 255
    assert 0 <= res[2] <= 255


# --- OkLab Logical / Property Tests ---


def _oklab_hue(rgb: tuple[int, int, int]) -> float:
    """Helper: compute the OkLab hue angle (degrees) for an sRGB color."""
    SRGB_LINEAR_CUTOFF = 0.04045

    def to_linear(val: float) -> float:
        val = val / 255.0
        return val / 12.92 if val <= SRGB_LINEAR_CUTOFF else pow((val + 0.055) / 1.055, 2.4)

    r_lin = to_linear(rgb[0])
    g_lin = to_linear(rgb[1])
    b_lin = to_linear(rgb[2])

    l_val = 0.4122214708 * r_lin + 0.5363325363 * g_lin + 0.0514459929 * b_lin
    m_val = 0.2119034982 * r_lin + 0.6806995451 * g_lin + 0.1073969566 * b_lin
    s_val = 0.0883024619 * r_lin + 0.0853627803 * g_lin + 0.8301696993 * b_lin

    l_ = pow(l_val, 1 / 3)
    m_ = pow(m_val, 1 / 3)
    s_ = pow(s_val, 1 / 3)

    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b_v = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    return math.degrees(math.atan2(b_v, a))


def _hls_saturation(rgb: tuple[int, int, int]) -> float:
    """Helper: return HLS saturation (0.0-1.0) for an sRGB color."""
    _, _, s = colorsys.rgb_to_hls(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    return s


def _hue_distance(h1: float, h2: float) -> float:
    """Shortest angular distance between two hue angles in degrees."""
    diff = abs(h1 - h2) % 360
    return min(diff, 360 - diff)


def test_nicify_oklab_hue_preservation():
    """nicify_oklab should preserve the perceptual hue of the input color.

    #556677 is blue-ish and should produce a blue-ish output.
    #557766 is green-ish and should produce a green-ish output.
    The output hues should not converge or collapse.
    """
    blue_ish = (0x55, 0x66, 0x77)  # #556677
    green_ish = (0x55, 0x77, 0x66)  # #557766

    result_blue = nicify_oklab(blue_ish)
    result_green = nicify_oklab(green_ish)

    input_hue_blue = _oklab_hue(blue_ish)
    input_hue_green = _oklab_hue(green_ish)
    output_hue_blue = _oklab_hue(result_blue)
    output_hue_green = _oklab_hue(result_green)

    # Hue should be approximately preserved (within 30 degrees)
    assert _hue_distance(input_hue_blue, output_hue_blue) < 30, (
        f"Blue-ish hue shifted too much: input={input_hue_blue:.1f}° -> output={output_hue_blue:.1f}°"
    )
    assert _hue_distance(input_hue_green, output_hue_green) < 30, (
        f"Green-ish hue shifted too much: input={input_hue_green:.1f}° -> output={output_hue_green:.1f}°"
    )


def test_nicify_oklab_distinct_outputs_for_distinct_inputs():
    """Two colors with clearly different dominant channels should produce
    clearly different outputs, not collapse to similar-looking colors."""
    blue_ish = (0x55, 0x66, 0x77)  # #556677 - dominant blue channel
    green_ish = (0x55, 0x77, 0x66)  # #557766 - dominant green channel

    result_blue = nicify_oklab(blue_ish)
    result_green = nicify_oklab(green_ish)

    # Outputs must be different
    assert result_blue != result_green, "Distinct inputs should produce distinct outputs"

    # The output hues should be far apart (these colors differ by ~105° in OkLab hue)
    output_hue_blue = _oklab_hue(result_blue)
    output_hue_green = _oklab_hue(result_green)
    hue_diff = _hue_distance(output_hue_blue, output_hue_green)
    assert hue_diff > 60, f"Output hues should remain well-separated, got only {hue_diff:.1f}° apart"


def test_nicify_oklab_muted_input_not_oversaturated():
    """A muted/desaturated input should not become maximally saturated.

    #556677 has very low saturation (~0.17 in HLS). After nicification with
    default params, it should remain moderate — not become fully saturated.
    """
    muted_color = (0x55, 0x66, 0x77)  # Low saturation input
    result = nicify_oklab(muted_color)

    sat = _hls_saturation(result)
    # A muted input should not become fully saturated
    assert sat < 0.95, f"Muted input ({muted_color}) became oversaturated: HLS S={sat:.3f}"


def test_nicify_oklab_saturation_params_are_effective():
    """The min_sat/max_sat parameters should meaningfully affect the output.

    With low max_sat (neutral scheme), output should be less saturated than
    with high min_sat (fluorescent scheme).
    """
    color = (200, 50, 50)  # A vivid red

    result_neutral = nicify_oklab(color, min_sat=0.05, max_sat=0.1)
    result_fluorescent = nicify_oklab(color, min_sat=0.7, max_sat=1.0)

    sat_neutral = _hls_saturation(result_neutral)
    sat_fluorescent = _hls_saturation(result_fluorescent)

    # Neutral should be significantly less saturated
    assert sat_neutral < sat_fluorescent, f"Neutral ({sat_neutral:.3f}) should be less saturated than fluorescent ({sat_fluorescent:.3f})"
    # And the difference should be meaningful (not just rounding)
    assert sat_fluorescent - sat_neutral > 0.15, (
        f"Saturation difference too small: neutral={sat_neutral:.3f}, fluorescent={sat_fluorescent:.3f}"
    )


def test_nicify_oklab_chroma_not_always_capped():
    """The output chroma should vary with input — not always be the same fixed value.

    A nearly-grey input and a vivid input should produce different chroma levels.
    """
    grey_ish = (128, 128, 130)  # Almost grey
    vivid = (255, 0, 0)  # Pure red

    result_grey = nicify_oklab(grey_ish)
    result_vivid = nicify_oklab(vivid)

    sat_grey = _hls_saturation(result_grey)
    sat_vivid = _hls_saturation(result_vivid)

    # Both should be valid
    assert 0 <= sat_grey <= 1.0
    assert 0 <= sat_vivid <= 1.0

    # The vivid input should produce higher saturation than the grey one
    assert sat_vivid > sat_grey, f"Vivid input should be more saturated than grey: vivid={sat_vivid:.3f}, grey={sat_grey:.3f}"


def test_nicify_oklab_user_reported_bug():
    """Regression test for user-reported issue: pypr color #556677 and
    pypr color #557766 should produce visually distinct palettes.

    #556677 is blue-dominant and should yield a blue-ish primary.
    #557766 is green-dominant and should yield a green-ish primary.
    """
    blue_ish = (0x55, 0x66, 0x77)
    green_ish = (0x55, 0x77, 0x66)

    result_blue = nicify_oklab(blue_ish)
    result_green = nicify_oklab(green_ish)

    # Blue-ish: the blue channel should be dominant in output
    assert result_blue[2] > result_blue[1], (
        f"#556677 output should have B > G: got RGB({result_blue[0]}, {result_blue[1]}, {result_blue[2]})"
    )

    # Green-ish: the green channel should be dominant in output
    assert result_green[1] > result_green[2], (
        f"#557766 output should have G > B: got RGB({result_green[0]}, {result_green[1]}, {result_green[2]})"
    )


# --- Theme / Existing Tests Preserved Below ---


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
        props = get_color_scheme_props(scheme)
        assert props == expected, f"Failed for scheme: {scheme}"


def test_color_scheme_props_default(wallpaper_plugin):
    props = get_color_scheme_props("default")
    assert props == {}


def test_generate_palette_basic(wallpaper_plugin):
    def mock_process_color(rgb):
        return (0.0, 0.5, 1.0)  # H=0, L=0.5, S=1.0

    rgb_list = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]
    wallpaper_plugin.config = {}

    palette = generate_palette(rgb_list, mock_process_color, theme=Theme.DARK)

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
    # variant="islands" passed as argument now

    palette = generate_palette(rgb_list, mock_process_color, variant_type="islands")

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
    assert _set_alpha("FFFFFF", "0.5") == "rgba(255, 255, 255, 0.5)"
    # Hex 7 (#)
    assert _set_alpha("#FFFFFF", "0.5") == "rgba(255, 255, 255, 0.5)"
    # RGBA already
    assert _set_alpha("rgba(0, 0, 0, 1.0)", "0.5") == "rgba(0, 0, 0, 0.5)"


def test_set_lightness(wallpaper_plugin):
    # Black -> lighter
    # #000000 is H=0, L=0, S=0. +20% lightness = L=0.2
    # Expect non-black
    res = _set_lightness("#000000", "20")
    assert res != "#000000"

    # White -> darker
    # #FFFFFF is L=1.0. -20% = L=0.8
    res = _set_lightness("#FFFFFF", "-20")
    assert res != "#ffffff"
    assert res != "#FFFFFF"


@pytest.mark.asyncio
async def test_apply_filters(wallpaper_plugin):
    replacements = {"color": "#FF0000"}

    # Simple replacement
    content = "Color is {{ color }}"
    res = await _apply_filters(content, replacements)
    assert res == "Color is #FF0000"

    # Filter set_alpha
    content = "Alpha: {{ color | set_alpha: 0.5 }}"
    res = await _apply_filters(content, replacements)
    assert "rgba(255, 0, 0, 0.5)" in res

    # Filter set_lightness
    content = "Light: {{ color | set_lightness: -50 }}"
    res = await _apply_filters(content, replacements)
    assert res != "Light: #FF0000"

    # Unknown filter (should return value as is)
    content = "Unknown: {{ color | invalid_filter: 123 }}"
    res = await _apply_filters(content, replacements)
    assert res == "Unknown: #FF0000"

    # Missing variable
    content = "Missing: {{ missing_var }}"
    res = await _apply_filters(content, replacements)
    assert res == "Missing: {{ missing_var }}"


def test_color_scheme_effect_on_saturation(wallpaper_plugin):
    """Verify that color schemes actually impact the visual properties of the generated colors."""
    # Base color: Bright Red (High Saturation)
    base_rgb = (255, 0, 0)

    # 1. Neutral (Low Saturation)
    props_neutral = get_color_scheme_props("neutral")
    res_neutral = nicify_oklab(base_rgb, **props_neutral)

    # Convert back to HLS to check saturation (0.0 - 1.0)
    # rgb_to_hls expects 0.0-1.0 inputs
    _, l_neutral, s_neutral = colorsys.rgb_to_hls(res_neutral[0] / 255.0, res_neutral[1] / 255.0, res_neutral[2] / 255.0)

    # 2. Fluo (High Saturation)
    props_fluo = get_color_scheme_props("fluo")
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


# --- Palette Display Tests ---


from pyprland.plugins.wallpapers.palette import (
    hex_to_rgb,
    generate_sample_palette,
    palette_to_json,
    palette_to_terminal,
    _categorize_palette,
)
import json


def test_hex_to_rgb():
    """Test hex color to RGB conversion."""
    # With hash
    assert hex_to_rgb("#FF0000") == (255, 0, 0)
    assert hex_to_rgb("#00FF00") == (0, 255, 0)
    assert hex_to_rgb("#0000FF") == (0, 0, 255)
    assert hex_to_rgb("#4285F4") == (66, 133, 244)

    # Without hash
    assert hex_to_rgb("FF0000") == (255, 0, 0)
    assert hex_to_rgb("4285F4") == (66, 133, 244)

    # Lowercase
    assert hex_to_rgb("#ff5500") == (255, 85, 0)


def test_generate_sample_palette():
    """Test sample palette generation."""
    base_rgb = (66, 133, 244)  # Google blue
    palette = generate_sample_palette(base_rgb, theme=Theme.DARK)

    # Check that palette contains expected keys
    assert "scheme" in palette
    assert palette["scheme"] == "dark"

    # Check color categories exist
    assert "colors.primary.dark.hex" in palette
    assert "colors.primary.light.hex" in palette
    assert "colors.secondary.dark.hex" in palette
    assert "colors.surface.dark.hex" in palette
    assert "colors.error.dark.hex" in palette

    # Check hex format
    assert palette["colors.primary.dark.hex"].startswith("#")
    assert len(palette["colors.primary.dark.hex"]) == 7

    # Check other formats exist
    assert "colors.primary.dark.rgb" in palette
    assert "colors.primary.dark.rgba" in palette
    assert "colors.primary.dark.hex_stripped" in palette

    # hex_stripped should not have #
    assert not palette["colors.primary.dark.hex_stripped"].startswith("#")


def test_generate_sample_palette_light_theme():
    """Test sample palette generation with light theme."""
    base_rgb = (66, 133, 244)
    palette = generate_sample_palette(base_rgb, theme=Theme.LIGHT)

    assert palette["scheme"] == "light"
    # Default should match light variant
    assert palette["colors.primary"] == palette["colors.primary.light.hex"]


def test_categorize_palette():
    """Test palette categorization."""
    # Create a minimal palette for testing
    palette = {
        "scheme": "dark",
        "colors.primary.dark.hex": "#AABBCC",
        "colors.secondary.dark.hex": "#DDEEFF",
        "colors.surface.dark.hex": "#112233",
        "colors.error.dark.hex": "#FF0000",
        "colors.red.dark.hex": "#FF6666",
        "colors.background.dark.hex": "#000000",
    }

    categories = _categorize_palette(palette)

    assert "colors.primary.dark.hex" in categories["primary"]
    assert "colors.secondary.dark.hex" in categories["secondary"]
    assert "colors.surface.dark.hex" in categories["surface"]
    assert "colors.error.dark.hex" in categories["error"]
    assert "colors.red.dark.hex" in categories["ansi"]
    assert "colors.background.dark.hex" in categories["utility"]


def test_palette_to_json():
    """Test JSON palette output."""
    base_rgb = (255, 85, 0)  # Orange
    palette = generate_sample_palette(base_rgb, theme=Theme.DARK)

    json_output = palette_to_json(palette)

    # Should be valid JSON
    parsed = json.loads(json_output)

    # Check structure
    assert "variables" in parsed
    assert "categories" in parsed
    assert "filters" in parsed
    assert "theme" in parsed

    # Check variables
    assert "colors.primary.dark.hex" in parsed["variables"]

    # Check categories
    assert "primary" in parsed["categories"]
    assert "secondary" in parsed["categories"]
    assert "ansi" in parsed["categories"]

    # Check filters documentation
    assert "set_alpha" in parsed["filters"]
    assert "set_lightness" in parsed["filters"]
    assert "example" in parsed["filters"]["set_alpha"]
    assert "description" in parsed["filters"]["set_lightness"]

    # Check theme
    assert parsed["theme"] == "dark"


def test_palette_to_terminal():
    """Test terminal palette output."""
    base_rgb = (66, 133, 244)
    palette = generate_sample_palette(base_rgb, theme=Theme.DARK)

    terminal_output = palette_to_terminal(palette)

    # Should contain category headers
    assert "Primary:" in terminal_output
    assert "Secondary:" in terminal_output
    assert "Surface:" in terminal_output
    assert "Error:" in terminal_output
    assert "ANSI Colors:" in terminal_output

    # Should contain ANSI escape codes (24-bit color)
    assert "\033[48;2;" in terminal_output
    assert "\033[0m" in terminal_output

    # Should contain variable names
    assert "colors.primary.dark.hex" in terminal_output

    # Should contain hex values
    assert "#" in terminal_output

    # Should contain filter examples
    assert "Filters:" in terminal_output
    assert "set_alpha" in terminal_output
    assert "set_lightness" in terminal_output
