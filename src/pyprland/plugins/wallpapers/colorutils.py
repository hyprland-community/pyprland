"""Utils for the wallpaper plugin."""

import math

try:
    # pylint: disable=unused-import
    from PIL import Image, ImageDraw, ImageOps
except ImportError:
    can_edit_image = False  # pylint: disable=invalid-name
    Image = None  # type: ignore # pylint: disable=invalid-name
    ImageDraw = None  # type: ignore # pylint: disable=invalid-name
    ImageOps = None  # type: ignore # pylint: disable=invalid-name
else:
    can_edit_image = True  # pylint: disable=invalid-name

SRGB_LINEAR_CUTOFF = 0.04045
SRGB_R_CUTOFF = 0.0031308

MIN_SATURATION = 20
MIN_BRIGHTNESS = 20
MIN_HUE_DIST = 21
HUE_DIFF_THRESHOLD = 128
HUE_MAX = 256
KERNEL_SUM = 16.0
TARGET_COLOR_COUNT = 3  # Number of dominant colors to extract from image


def _build_hue_histogram(hsv_pixels: list[tuple[int, int, int]]) -> tuple[list[float], list[list[int]]]:
    """Build a weighted hue histogram from HSV pixels.

    Args:
        hsv_pixels: List of (Hue, Saturation, Value) tuples
    """
    hue_weights = [0.0] * HUE_MAX
    hue_pixel_indices: list[list[int]] = [[] for _ in range(HUE_MAX)]

    for idx, (h, s, v) in enumerate(hsv_pixels):
        if s < MIN_SATURATION or v < MIN_BRIGHTNESS:
            continue

        weight = (s * v) / (255.0 * 255.0)
        hue_weights[h] += weight
        hue_pixel_indices[h].append(idx)

    return hue_weights, hue_pixel_indices


def _smooth_histogram(hue_weights: list[float]) -> list[float]:
    """Smooth the histogram using a Gaussian-like kernel.

    Args:
        hue_weights: List of weights for each hue
    """
    smoothed_weights = [0.0] * HUE_MAX
    kernel = [1, 4, 6, 4, 1]

    for i in range(HUE_MAX):
        w_sum = 0.0
        for k_idx, offset in enumerate(range(-2, 3)):
            idx = (i + offset) % HUE_MAX
            w_sum += hue_weights[idx] * kernel[k_idx]
        smoothed_weights[i] = w_sum / KERNEL_SUM

    return smoothed_weights


def _find_peaks(smoothed_weights: list[float]) -> list[tuple[float, int]]:
    """Find peaks in the smoothed histogram.

    Args:
        smoothed_weights: List of smoothed weights
    """
    peaks: list[tuple[float, int]] = []
    for i in range(HUE_MAX):
        left = smoothed_weights[(i - 1) % HUE_MAX]
        right = smoothed_weights[(i + 1) % HUE_MAX]
        val = smoothed_weights[i]
        if val >= left and val >= right and val > 0:
            peaks.append((val, i))

    peaks.sort(reverse=True)
    return peaks


def _get_best_pixel_for_hue(
    target_hue: int,
    hue_pixel_indices: list[list[int]],
    hsv_pixels: list[tuple[int, int, int]],
    rgb_pixels: list[tuple[int, int, int]],
) -> tuple[int, int, int]:
    """Find the most representative pixel for a given hue bin.

    Args:
        target_hue: The target hue value
        hue_pixel_indices: Mapping of hue to pixel indices
        hsv_pixels: List of HSV pixels
        rgb_pixels: List of RGB pixels
    """
    best_pixel_idx = -1
    max_sv = -1.0
    for offset in range(-2, 3):
        check_h = (target_hue + offset) % HUE_MAX
        for px_idx in hue_pixel_indices[check_h]:
            _, s, v = hsv_pixels[px_idx]
            weight = s * v
            if weight > max_sv:
                max_sv = weight
                best_pixel_idx = px_idx

    if best_pixel_idx != -1:
        return rgb_pixels[best_pixel_idx]

    if hue_pixel_indices[target_hue]:
        return rgb_pixels[hue_pixel_indices[target_hue][0]]

    return (0, 0, 0)


def _calculate_hue_diff(hue1: int, hue2: int) -> int:
    """Calculate the shortest distance between two hues on the circle.

    Args:
        hue1: First hue value
        hue2: Second hue value
    """
    diff = abs(hue1 - hue2)
    if diff > HUE_DIFF_THRESHOLD:
        diff = HUE_MAX - diff
    return diff


def _select_colors_from_peaks(
    peaks: list[tuple[float, int]],
    hue_pixel_indices: list[list[int]],
    hsv_pixels: list[tuple[int, int, int]],
    rgb_pixels: list[tuple[int, int, int]],
) -> list[tuple[int, int, int]]:
    """Select distinct colors from the identified peaks.

    Args:
        peaks: List of (weight, hue) tuples
        hue_pixel_indices: Mapping of hue to pixel indices
        hsv_pixels: List of HSV pixels
        rgb_pixels: List of RGB pixels
    """
    final_colors: list[tuple[int, int, int]] = []
    final_hues: list[int] = []

    if not peaks:
        return final_colors

    # 1. First Color: The dominant one
    _, p_hue = peaks.pop(0)
    final_hues.append(p_hue)
    final_colors.append(_get_best_pixel_for_hue(p_hue, hue_pixel_indices, hsv_pixels, rgb_pixels))

    # 2. Second Color: The next dominant distinct one
    second_peak_idx = -1
    for i, (_, p_hue) in enumerate(peaks):
        diff = _calculate_hue_diff(p_hue, final_hues[0])
        if diff > MIN_HUE_DIST:
            second_peak_idx = i
            break

    if second_peak_idx != -1:
        _, p_hue = peaks.pop(second_peak_idx)
        final_hues.append(p_hue)
        final_colors.append(_get_best_pixel_for_hue(p_hue, hue_pixel_indices, hsv_pixels, rgb_pixels))

    # 3. Third Color: The most distinct hue
    if len(final_colors) >= TARGET_COLOR_COUNT - 1 and peaks:
        best_dist = -1.0
        best_peak_idx = -1

        for i, (_, p_hue) in enumerate(peaks):
            dists = [_calculate_hue_diff(p_hue, h) for h in final_hues]
            min_d = min(dists)
            if min_d > best_dist:
                best_dist = min_d
                best_peak_idx = i

        if best_peak_idx != -1 and best_dist > MIN_HUE_DIST:
            _, p_hue = peaks.pop(best_peak_idx)
            final_hues.append(p_hue)
            final_colors.append(_get_best_pixel_for_hue(p_hue, hue_pixel_indices, hsv_pixels, rgb_pixels))

    return final_colors


def get_dominant_colors(img_path: str) -> list[tuple[int, int, int]]:
    """Pick representative pixels using a weighted Hue Histogram approach.

    Args:
        img_path: Path to the image file
    """
    if not Image:
        return [(0, 0, 0)] * 3

    try:
        with Image.open(img_path) as initial_img:
            img = initial_img.convert("RGB")
            resample = getattr(Image, "Resampling", Image).LANCZOS
            img.thumbnail((200, 200), resample)

            hsv_img = img.convert("HSV")
            hsv_pixels: list[tuple[int, int, int]] = list(hsv_img.getdata())
            rgb_pixels: list[tuple[int, int, int]] = list(img.getdata())

            if not hsv_pixels:
                return [(0, 0, 0)] * 3

            hue_weights, hue_pixel_indices = _build_hue_histogram(hsv_pixels)
            smoothed_weights = _smooth_histogram(hue_weights)
            peaks = _find_peaks(smoothed_weights)

            final_colors = _select_colors_from_peaks(peaks, hue_pixel_indices, hsv_pixels, rgb_pixels)

            while len(final_colors) < TARGET_COLOR_COUNT:
                final_colors.append(final_colors[0] if final_colors else (0, 0, 0))

            return final_colors

    except (OSError, ValueError) as e:  # PIL can raise various exceptions
        # Log would require passing logger; return default silently
        _ = e  # Acknowledge the exception was captured
        return [(0, 0, 0)] * TARGET_COLOR_COUNT


def nicify_oklab(
    rgb: tuple[int, int, int],
    min_sat: float = 0.3,
    max_sat: float = 0.7,
    min_light: float = 0.2,
    max_light: float = 0.8,
) -> tuple[int, int, int]:
    """Transform RGB color using perceptually-uniform OkLab color space.

    Produces more consistent and natural-looking results across all hues.

    Args:
        rgb: Tuple of (R, G, B) with values 0-255
        min_sat: Minimum saturation (0.0-1.0, default 0.3)
        max_sat: Maximum saturation (0.0-1.0, default 0.7)
        min_light: Minimum lightness (0.0-1.0, default 0.2)
        max_light: Maximum lightness (0.0-1.0, default 0.8)

    Returns:
        Tuple of (R, G, B) with values 0-255
    """
    # pylint: disable=too-many-locals

    # Convert sRGB to linear RGB
    def to_linear(val: float) -> float:
        val = val / 255.0
        return val / 12.92 if val <= SRGB_LINEAR_CUTOFF else pow((val + 0.055) / 1.055, 2.4)

    r_lin = to_linear(rgb[0])
    g_lin = to_linear(rgb[1])
    b_lin = to_linear(rgb[2])

    # Convert to OkLab
    l_val = 0.4122214708 * r_lin + 0.5363325363 * g_lin + 0.0514459929 * b_lin
    m_val = 0.2119034982 * r_lin + 0.6806995451 * g_lin + 0.1073969566 * b_lin
    s_val = 0.0883024619 * r_lin + 0.0853627803 * g_lin + 0.8301696993 * b_lin

    l_ = pow(l_val, 1 / 3)
    m_ = pow(m_val, 1 / 3)
    s_ = pow(s_val, 1 / 3)

    l_cap = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    b_val = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_

    # Extract chroma and hue
    chroma = math.sqrt(a * a + b_val * b_val)
    hue = math.atan2(b_val, a)

    # Scale chroma based on saturation constraints
    target_chroma = (chroma / 0.4) * (max_sat - min_sat) + min_sat
    clamped_chroma = min(target_chroma, 0.3)

    # Clamp lightness
    clamped_l = max(min_light, min(max_light, l_cap))

    # Reconstruct with new chroma
    a_new = clamped_chroma * math.cos(hue)
    b_new = clamped_chroma * math.sin(hue)

    # Convert back from OkLab
    l_new = clamped_l + 0.3963377774 * a_new + 0.2158037573 * b_new
    m_new = clamped_l - 0.1055613458 * a_new - 0.0638541728 * b_new
    s_new = clamped_l - 0.0894841775 * a_new - 1.2914855480 * b_new

    l_lin = pow(l_new, 3)
    m_lin = pow(m_new, 3)
    s_lin = pow(s_new, 3)

    r_out = 4.0767416621 * l_lin - 3.3077363322 * m_lin + 0.2309101289 * s_lin
    g_out = -1.2684380046 * l_lin + 2.6097574011 * m_lin - 0.3413193761 * s_lin
    b_out = -0.0041960771 * l_lin - 0.7034186147 * m_lin + 1.7076147010 * s_lin

    # Convert back to sRGB
    def to_srgb(val: float) -> float:
        return 12.92 * val if val <= SRGB_R_CUTOFF else 1.055 * pow(val, 1 / 2.4) - 0.055

    return (
        round(max(0, min(255, to_srgb(r_out) * 255))),
        round(max(0, min(255, to_srgb(g_out) * 255))),
        round(max(0, min(255, to_srgb(b_out) * 255))),
    )
