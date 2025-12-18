"""Plugin template."""

import asyncio
import colorsys
import contextlib
import math
import os
import os.path
import random
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageCms, ImageDraw, ImageOps

    can_edit_image = True
except ImportError:
    can_edit_image = False
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    ImageOps = None  # type: ignore
    ImageCms = None  # type: ignore

from ..aioops import aiexists, ailistdir, aiopen
from ..common import CastBoolMixin, apply_variables, prepare_for_quotes, state
from .interface import Plugin

IMAGE_FORMAT = "jpg"
HEX_LEN = 6
HEX_LEN_HASH = 7
HYPRPAPER_SOCKET = os.path.join(
    os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.environ.get('UID')}"),
    "hypr",
    os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "default"),
    ".hyprpaper.sock",
)
SRGB_LINEAR_CUTOFF = 0.04045
SRGB_R_CUTOFF = 0.0031308


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

    # Convert sRGB to linear RGB
    def to_linear(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= SRGB_LINEAR_CUTOFF else pow((c + 0.055) / 1.055, 2.4)

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
    def to_srgb(c: float) -> float:
        return 12.92 * c if c <= SRGB_R_CUTOFF else 1.055 * pow(c, 1 / 2.4) - 0.055

    return (
        int(round(max(0, min(255, to_srgb(r_out) * 255)))),
        int(round(max(0, min(255, to_srgb(g_out) * 255)))),
        int(round(max(0, min(255, to_srgb(b_out) * 255)))),
    )


def expand_path(path: str) -> str:
    """Expand the path."""
    return os.path.expanduser(os.path.expandvars(path))


async def get_files_with_ext(path: str, extensions: list[str], recurse: bool = True) -> AsyncIterator[str]:
    """Return files matching `extension` in given `path`. Can optionally `recurse` subfolders.."""
    for fname in await ailistdir(path):
        ext = fname.rsplit(".", 1)[-1]
        full_path = os.path.join(path, fname)
        if ext.lower() in extensions:
            yield full_path
        elif recurse and os.path.isdir(full_path):
            async for v in get_files_with_ext(full_path, extensions, True):
                yield v


@dataclass(slots=True)
class MonitorInfo:
    """Monitor information."""

    name: str
    width: int
    height: int
    transform: int
    scale: float


async def fetch_monitors(extension: "Extension") -> list[MonitorInfo]:
    """Fetch monitor information from hyprctl."""
    monitors = await extension.hyprctl_json("monitors")
    return [
        MonitorInfo(name=m["name"], width=int(m["width"]), height=int(m["height"]), transform=m["transform"], scale=m["scale"])
        for m in monitors
    ]


class RoundedImageManager:
    """Manages rounded and scaled images for monitors."""

    def __init__(self, radius: int) -> None:
        """Initialize the manager."""
        self.radius = radius

        self.tmpdir = Path("~").expanduser() / ".cache" / "pyprland" / "wallpapers"
        self.tmpdir.mkdir(parents=True, exist_ok=True)

    def _build_key(self, monitor: MonitorInfo, image_path: str) -> str:
        return f"{monitor.transform}:{monitor.scale}x{monitor.width}x{monitor.height}:{image_path}"

    def get_path(self, key: str) -> str:
        """Get the path for a given key."""
        return os.path.join(self.tmpdir, f"{abs(hash((key, self.radius)))}.{IMAGE_FORMAT}")

    def scale_and_round(self, src: str, monitor: MonitorInfo) -> str:
        """Scale and round the image for the given monitor."""
        key = self._build_key(monitor, src)
        dest = self.get_path(key)
        if not os.path.exists(dest):
            with Image.open(src) as img:  # type: ignore
                is_rotated = monitor.transform % 2
                width, height = (monitor.width, monitor.height) if not is_rotated else (monitor.height, monitor.width)
                width = int(width / monitor.scale)
                height = int(height / monitor.scale)
                resample = Image.Resampling.LANCZOS  # type: ignore
                resized = ImageOps.fit(img, (width, height), method=resample)  # type: ignore

                scale = 4
                image_width, image_height = resized.width * scale, resized.height * scale
                rounded_mask = Image.new("L", (image_width, image_height), 0)  # type: ignore
                corner_draw = ImageDraw.Draw(rounded_mask)  # type: ignore
                corner_draw.rounded_rectangle((0, 0, image_width - 1, image_height - 1), radius=self.radius * scale, fill=255)
                mask = rounded_mask.resize(resized.size, resample=resample)

                result = Image.new("RGB", resized.size, "black")  # type: ignore
                result.paste(resized.convert("RGB"), mask=mask)
                result.convert("RGB").save(dest)

        return dest


class Extension(CastBoolMixin, Plugin):
    """Manages the background image."""

    default_image_ext: set[str] | list[str] = {"png", "jpg", "jpeg"}
    image_list: list[str] = []
    running = True
    proc: list = []
    loop = None

    next_background_event = asyncio.Event()
    cur_image = ""
    _paused = False

    rounded_manager: RoundedImageManager | None

    async def _send_hyprpaper(self, message: bytes) -> None:
        """Create hyprpaper sockets, send a message and wait for full write."""
        for _ in range(3):
            try:
                hyprpaper_socket_reader, hyprpaper_socket_writer = await asyncio.open_unix_connection(HYPRPAPER_SOCKET)
                hyprpaper_socket_writer.write(message)
                await hyprpaper_socket_writer.drain()
                hyprpaper_socket_writer.close()
            except ConnectionRefusedError:
                # start hyprpaper
                asyncio.create_task(asyncio.create_subprocess_exec("hyprpaper"))
                asyncio.create_task(asyncio.create_subprocess_exec("hyprctl reload"))
                await asyncio.sleep(1)
            except Exception:
                self.log.exception("Failed to connect to hyprpaper socket at %s", HYPRPAPER_SOCKET)
            else:
                break

    async def on_reload(self) -> None:
        """Re-build the image list."""
        cfg_path = self.config["path"]
        paths = [expand_path(cfg_path)] if isinstance(cfg_path, str) else [expand_path(p) for p in cfg_path]
        extensions = self.config.get("extensions", self.default_image_ext)
        radius = int(self.config.get("radius", 0))

        self.image_list = [
            os.path.join(path, fname)
            for path in paths
            async for fname in get_files_with_ext(path, extensions, recurse=self.cast_bool(self.config.get("recurse")))
        ]

        if radius > 0 and can_edit_image:
            self.rounded_manager = RoundedImageManager(radius)
        else:
            self.rounded_manager = None

        # Start the main loop if it's the first load of the config
        if self.loop is None:
            self.loop = asyncio.create_task(self.main_loop())

    async def exit(self) -> None:
        """Terminates gracefully."""
        self.running = False
        if self.loop:
            self.loop.cancel()
        await self.terminate()

    async def event_monitoradded(self, _: str) -> None:
        """When a new monitor is added, set the background."""
        self.next_background_event.set()

    def select_next_image(self) -> str:
        """Return the next image (random is supported for now)."""
        choice = random.choice(self.image_list)
        if choice == self.cur_image:
            choice = random.choice(self.image_list)
        self.cur_image = choice
        return choice

    async def _prepare_wallpaper(self, monitor: MonitorInfo, img_path: str) -> str:
        if not self.rounded_manager:
            return prepare_for_quotes(img_path)

        processed = self.rounded_manager.scale_and_round(img_path, monitor)
        return prepare_for_quotes(processed)

    async def _run_one(self, template: str, values: dict[str, str]) -> None:
        """Run one command."""
        cmd = apply_variables(template, values)
        self.log.info("Running %s", cmd)
        self.proc.append(await asyncio.create_subprocess_shell(cmd))

    def _get_dominant_colors(self, img_path: str) -> list[tuple[int, int, int]]:
        """Pick representative pixels from the strongest LAB clusters."""
        try:
            with Image.open(img_path) as initial_img:  # type: ignore
                img = initial_img.convert("RGB")
                resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS  # type: ignore
                img.thumbnail((200, 200), resample)

                if not hasattr(self, "_rgb_to_lab_transform") or not hasattr(self, "_lab_to_rgb_transform"):
                    srgb_profile = ImageCms.createProfile("sRGB")  # type: ignore
                    lab_profile = ImageCms.createProfile("LAB")  # type: ignore
                    self._rgb_to_lab_transform = ImageCms.buildTransformFromOpenProfiles(srgb_profile, lab_profile, "RGB", "LAB")  # type: ignore
                    self._lab_to_rgb_transform = ImageCms.buildTransformFromOpenProfiles(lab_profile, srgb_profile, "LAB", "RGB")  # type: ignore

                lab_img = ImageCms.applyTransform(img, self._rgb_to_lab_transform)  # type: ignore
                # The type stubs for PIL.Image.getdata() return Sequence[Any] which is compatible with list()
                # but pyright is strict about the exact return type for list().
                # Using explicit type ignoring here as we know getdata() returns an iterable compatible with list()
                lab_pixels: list[tuple[int, int, int]] = list(lab_img.getdata())  # type: ignore
                rgb_pixels: list[tuple[int, int, int]] = list(img.getdata())  # type: ignore

                if not lab_pixels:
                    return [(0, 0, 0)] * 3

                lab_vectors = [tuple(float(c) for c in lab) for lab in lab_pixels]
                k = min(12, len(lab_vectors))
                centroids = random.sample(lab_vectors, k)

                cluster_members = [[] for _ in range(k)]
                cluster_indices = [[] for _ in range(k)]

                for _ in range(6):
                    for members, indices in zip(cluster_members, cluster_indices, strict=False):
                        members.clear()
                        indices.clear()

                    for idx, vec in enumerate(lab_vectors):
                        distances = [
                            (vec[0] - centroid[0]) ** 2 + (vec[1] - centroid[1]) ** 2 + (vec[2] - centroid[2]) ** 2
                            for centroid in centroids
                        ]
                        winner = min(range(k), key=distances.__getitem__)
                        cluster_members[winner].append(vec)
                        cluster_indices[winner].append(idx)

                    for idx_cluster, members in enumerate(cluster_members):
                        if members:
                            centroids[idx_cluster] = tuple(sum(component[i] for component in members) / len(members) for i in range(3))
                        else:
                            centroids[idx_cluster] = random.choice(lab_vectors)

                cluster_info = [(len(indices), cluster_idx) for cluster_idx, indices in enumerate(cluster_indices) if indices]
                if not cluster_info:
                    return [(0, 0, 0)] * 3

                cluster_info.sort(reverse=True)

                # Pick top clusters that are distinct enough
                top_clusters: list[int] = []
                # Keep track of picked LAB colors to compare distances
                picked_lab: list[tuple[float, float, float]] = []

                # Minimum distance threshold (in LAB space, mainly considering a/b channels)
                # 20 ensures distinct hues/chroma.
                MIN_DIST = 20.0

                for _, cluster_idx in cluster_info:
                    if len(top_clusters) >= 3:
                        break

                    # Calculate representative color for this cluster to check distance
                    centroid = centroids[cluster_idx]
                    candidate_indices = cluster_indices[cluster_idx]
                    best_idx = min(
                        candidate_indices,
                        key=lambda idx: (
                            (lab_vectors[idx][0] - centroid[0]) ** 2
                            + (lab_vectors[idx][1] - centroid[1]) ** 2
                            + (lab_vectors[idx][2] - centroid[2]) ** 2
                        ),
                    )
                    candidate_lab = lab_vectors[best_idx]
                    candidate_chroma = math.sqrt(candidate_lab[1] ** 2 + candidate_lab[2] ** 2)
                    candidate_hue = math.atan2(candidate_lab[2], candidate_lab[1])

                    # Check distance against already picked colors
                    is_distinct = True
                    for i, picked in enumerate(picked_lab):
                        # Compare only a and b channels (indices 1 and 2)
                        # This avoids treating light/dark versions of the same color as distinct
                        # which is important because the palette generation normalizes lightness.
                        dist = math.sqrt((candidate_lab[1] - picked[1]) ** 2 + (candidate_lab[2] - picked[2]) ** 2)
                        # If comparing with the primary color (first picked), enforce stricter threshold
                        # to ensure secondary/tertiary colors are distinct enough from the primary
                        current_threshold = MIN_DIST * 1.5 if i == 0 else MIN_DIST

                        if dist < current_threshold:
                            is_distinct = False
                            break

                        # Also enforce Hue distinction for chromatic colors
                        picked_chroma = math.sqrt(picked[1] ** 2 + picked[2] ** 2)
                        if candidate_chroma > 10 and picked_chroma > 10:
                            picked_hue = math.atan2(picked[2], picked[1])
                            hue_diff = abs(candidate_hue - picked_hue)
                            # Handle wrap-around (e.g. difference between -pi and +pi should be small)
                            if hue_diff > math.pi:
                                hue_diff = 2 * math.pi - hue_diff

                            # 0.4 rad (~23 degrees) separation
                            if hue_diff < 0.4:
                                is_distinct = False
                                break

                    if is_distinct:
                        top_clusters.append(cluster_idx)
                        picked_lab.append(candidate_lab)

                # If we didn't find enough distinct clusters, fill with the most dominant ones again
                # skipping the check, or just duplicate the last one if we run out of clusters completely
                if len(top_clusters) < 3:
                    remaining_needed = 3 - len(top_clusters)
                    # Get clusters that weren't picked yet
                    remaining_clusters = [idx for _, idx in cluster_info if idx not in top_clusters]
                    top_clusters.extend(remaining_clusters[:remaining_needed])

                results = []
                for chosen_cluster in top_clusters:
                    centroid = centroids[chosen_cluster]
                    candidate_indices = cluster_indices[chosen_cluster]
                    best_idx = min(
                        candidate_indices,
                        key=lambda idx: (
                            (lab_vectors[idx][0] - centroid[0]) ** 2
                            + (lab_vectors[idx][1] - centroid[1]) ** 2
                            + (lab_vectors[idx][2] - centroid[2]) ** 2
                        ),
                    )
                    results.append(rgb_pixels[best_idx])

                while len(results) < 3:
                    results.append(results[0] if results else (0, 0, 0))

                return results
        except Exception:
            self.log.exception("Error extracting dominant color")
            return [(0, 0, 0)] * 3

    async def _detect_theme(self) -> str:
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
        except Exception:
            self.log.debug("gsettings not available for theme detection")

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
        except Exception:
            self.log.debug("darkman not available for theme detection")

        return "dark"

    def _get_color_scheme_props(self) -> dict[str, float]:
        """Return color scheme properties suitable for nicify_oklab."""
        oklab_args: dict[str, float] = {}
        color_scheme = self.config.get("color_scheme", "").lower()

        if color_scheme == "pastel":
            oklab_args = {
                "min_sat": 0.2,
                "max_sat": 0.5,
                "min_light": 0.6,
                "max_light": 0.9,
            }
        elif color_scheme.startswith("fluo"):
            oklab_args = {
                "min_sat": 0.7,
                "max_sat": 1.0,
                "min_light": 0.4,
                "max_light": 0.85,
            }
        elif color_scheme == "neutral":
            oklab_args = {
                "min_sat": 0.05,
                "max_sat": 0.1,
                "min_light": 0.4,
                "max_light": 0.65,
            }
        elif color_scheme == "earth":
            oklab_args = {
                "min_sat": 0.2,
                "max_sat": 0.6,
                "min_light": 0.2,
                "max_light": 0.6,
            }
        return oklab_args

    def _generate_palette(self, rgb_list: list[tuple[int, int, int]], theme: str = "dark") -> dict[str, str]:
        """Generate a material-like palette from a single color."""
        oklab_args = self._get_color_scheme_props()

        def process_color(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
            # reduce blue level for earth
            if self.config.get("color_scheme") == "earth":
                rgb = (rgb[0], rgb[1], int(rgb[2] * 0.7))

            r, g, b = nicify_oklab(rgb, **oklab_args)
            return colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)

        hue, light, sat = process_color(rgb_list[0])

        if self.config.get("variant") == "islands":
            h_sec, _, s_sec = process_color(rgb_list[1])
            h_tert, _, s_tert = process_color(rgb_list[2])
        else:
            h_sec, s_sec = hue, sat
            h_tert, s_tert = hue, sat

        def to_hex(r: float, g: float, b: float) -> str:
            return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

        def to_rgb(r: float, g: float, b: float) -> str:
            return f"rgb({int(r * 255)}, {int(g * 255)}, {int(b * 255)})"

        def to_rgba(r: float, g: float, b: float) -> str:
            return f"rgba({int(r * 255)}, {int(g * 255)}, {int(b * 255)}, 1.0)"

        def get_variant(h: float, s: float, l: float) -> tuple[float, float, float]:  # noqa: E741
            return colorsys.hls_to_rgb(h, max(0.0, min(1.0, l)), s)

        colors = {"scheme": theme}

        # (hue_offset, saturation_mult, light_dark_mode, light_light_mode)
        variations = {
            "source": (0.0, 1.0, light, light),
            "primary": (0.0, 1.0, 0.80, 0.40),
            "on_primary": (0.0, 0.2, 0.20, 1.00),
            "primary_container": (0.0, 1.0, 0.30, 0.90),
            "on_primary_container": (0.0, 1.0, 0.90, 0.10),
            "secondary": (-0.15, 0.8, 0.80, 0.40),
            "on_secondary": (-0.15, 0.2, 0.20, 1.00),
            "secondary_container": (-0.15, 0.8, 0.30, 0.90),
            "on_secondary_container": (-0.15, 0.8, 0.90, 0.10),
            "tertiary": (0.15, 0.8, 0.80, 0.40),
            "on_tertiary": (0.15, 0.2, 0.20, 1.00),
            "tertiary_container": (0.15, 0.8, 0.30, 0.90),
            "on_tertiary_container": (0.15, 0.8, 0.90, 0.10),
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
            "primary_fixed": (0.0, 1.0, 0.90, 0.90),
            "primary_fixed_dim": (0.0, 1.0, 0.80, 0.80),
            "on_primary_fixed": (0.0, 1.0, 0.10, 0.10),
            "on_primary_fixed_variant": (0.0, 1.0, 0.30, 0.30),
            "secondary_fixed": (0.5, 0.8, 0.90, 0.90),
            "secondary_fixed_dim": (0.5, 0.8, 0.80, 0.80),
            "on_secondary_fixed": (0.5, 0.8, 0.10, 0.10),
            "on_secondary_fixed_variant": (0.5, 0.8, 0.30, 0.30),
            "tertiary_fixed": (0.25, 0.8, 0.90, 0.90),
            "tertiary_fixed_dim": (0.25, 0.8, 0.80, 0.80),
            "on_tertiary_fixed": (0.25, 0.8, 0.10, 0.10),
            "on_tertiary_fixed_variant": (0.25, 0.8, 0.30, 0.30),
            "red": ("=0.0", 1.0, 0.80, 0.40),
            "green": ("=0.333", 1.0, 0.80, 0.40),
            "yellow": ("=0.166", 1.0, 0.80, 0.40),
            "blue": ("=0.666", 1.0, 0.80, 0.40),
            "magenta": ("=0.833", 1.0, 0.80, 0.40),
            "cyan": ("=0.5", 1.0, 0.80, 0.40),
        }

        for name, (h_off, s_mult, l_dark, l_light) in variations.items():
            used_h = hue
            used_s = sat
            used_off = h_off

            if self.config.get("variant") == "islands":
                if "secondary" in name and "fixed" not in name:
                    used_h = h_sec
                    used_s = s_sec
                    used_off = 0.0
                elif "tertiary" in name and "fixed" not in name:
                    used_h = h_tert
                    used_s = s_tert
                    used_off = 0.0

            cur_h = float(used_off[1:]) if isinstance(used_off, str) and used_off.startswith("=") else (used_h + float(used_off)) % 1.0
            cur_s = max(0.0, min(1.0, used_s * s_mult))

            r_dark, g_dark, b_dark = get_variant(cur_h, cur_s, l_dark)
            r_light, g_light, b_light = get_variant(cur_h, cur_s, l_light)

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

        return colors

    def _set_alpha(self, color: str, alpha: str) -> str:
        """Set alpha channel for a color."""
        if color.startswith("rgba("):
            return f"{color.rsplit(',', 1)[0]}, {alpha})"
        if len(color) == HEX_LEN:
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            return f"rgba({r}, {g}, {b}, {alpha})"
        if len(color) == HEX_LEN_HASH and color.startswith("#"):
            r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
            return f"rgba({r}, {g}, {b}, {alpha})"
        return color

    def _set_lightness(self, hex_color: str, amount: str) -> str:
        """Adjust lightness of a color."""
        # hex_color can be RRGGBB or #RRGGBB
        color = hex_color.lstrip("#")
        if len(color) != HEX_LEN:
            return hex_color

        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        h, l_val, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)

        # amount is percentage change, e.g. 20.0 or -10.0
        with contextlib.suppress(ValueError):
            l_val = max(0.0, min(1.0, l_val + (float(amount) / 100.0)))

        nr, ng, nb = colorsys.hls_to_rgb(h, l_val, s)
        new_hex = f"{int(nr * 255):02x}{int(ng * 255):02x}{int(nb * 255):02x}"
        return f"#{new_hex}" if hex_color.startswith("#") else new_hex

    async def _apply_filters(self, content: str, replacements: dict[str, str]) -> str:
        """Apply filters to the content."""
        # Process all template tags {{ ... }}
        # We find all tags first, then replace them.
        # This regex matches {{ variable | filter: arg }} or just {{ variable }}
        # It handles spaces around variable and filter parts.
        tag_pattern = re.compile(r"\{\{\s*([\w\.]+)(?:\s*\|\s*([\w_]+)\s*:\s*([^}]+))?\s*\}\}")

        def replace_tag(match: re.Match) -> str:
            key = match.group(1)
            filter_name = match.group(2)
            filter_arg = match.group(3)

            value = replacements.get(key)
            if value is None:
                return match.group(0)

            if filter_name and filter_arg:
                filter_arg = filter_arg.strip()
                with contextlib.suppress(Exception):
                    if filter_name == "set_alpha":
                        return self._set_alpha(value, filter_arg)
                    if filter_name == "set_lightness":
                        return self._set_lightness(value, filter_arg)
                # Fallback if filter fails or unknown
                return str(value)

            return str(value)

        return tag_pattern.sub(replace_tag, content)

    async def _generate_templates(self, img_path: str, color: str | None = None) -> None:
        """Generate templates from the image."""
        templates = self.config.get("templates")
        if not templates:
            return

        if not can_edit_image:
            self.log.warning("PIL not installed, cannot generate color palette")
            return

        if color:
            if color.startswith("#"):
                c_rgb = (int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16))
            else:
                c_rgb = (int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16))
            dominant_colors = [c_rgb] * 3
        else:
            dominant_colors = await asyncio.to_thread(self._get_dominant_colors, img_path)
        theme = await self._detect_theme()
        replacements = self._generate_palette(dominant_colors, theme)
        replacements["image"] = img_path

        for name, template_config in templates.items():
            self.log.debug("processing %s", name)
            if "input_path" not in template_config or "output_path" not in template_config:
                self.log.error("Template %s missing input_path or output_path", name)
                continue

            input_path = expand_path(template_config["input_path"])
            output_path = expand_path(template_config["output_path"])

            if not await aiexists(input_path):
                self.log.error("Template input file %s not found", input_path)
                continue

            try:
                async with aiopen(input_path, "r") as f:
                    content = await f.read()

                content = await self._apply_filters(content, replacements)

                async with aiopen(output_path, "w") as f:
                    await f.write(content)
                self.log.info("Generated %s from %s", output_path, input_path)

                post_hook = template_config.get("post_hook")
                if post_hook:
                    self.log.info("Running post_hook for %s: %s", name, post_hook)
                    await asyncio.create_subprocess_shell(post_hook)

            except Exception:
                self.log.exception("Error processing template %s", name)

    async def update_vars(self, variables: dict[str, Any], monitor: MonitorInfo, img_path: str) -> dict[str, Any]:
        """Get fresh variables for the given monitor."""
        unique = self.config.get("unique", False)
        if unique:
            img_path = self.select_next_image()
        filename = await self._prepare_wallpaper(monitor, img_path)
        variables.update({"file": filename, "output": monitor.name})
        return variables

    async def _iter_one(self, variables: dict[str, Any]) -> None:
        cmd_template = self.config.get("command")
        img_path = self.select_next_image()
        monitors: list[MonitorInfo] = await fetch_monitors(self)

        if cmd_template:
            filtered_monitors = monitors if "[output]" in cmd_template else [monitors[0]]
            for monitor in filtered_monitors:
                variables = await self.update_vars(variables, monitor, img_path)
                await self._run_one(cmd_template, variables)
        else:
            # use hyprpaper
            command_collector = []
            for monitor in monitors:
                variables = await self.update_vars(variables, monitor, img_path)
                self.log.debug("Setting wallpaper %s for monitor %s", variables["file"], variables.get("output"))
                command_collector.append(apply_variables("preload [file]", variables))
                command_collector.append(apply_variables("wallpaper [output], [file]", variables))

            for cmd in command_collector:
                self.log.info("Running hyprpaper command: %s", cmd)
                await self._send_hyprpaper(cmd.encode())

        # Generate templates after wallpaper is selected
        await self._generate_templates(img_path)

        # check if the command failed
        for proc in self.proc:
            if proc.returncode:
                await self.notify_error("wallpaper command failed")
                break

        if self.config.get("post_command"):
            command = apply_variables(self.config["post_command"], variables)
            proc = await asyncio.create_subprocess_shell(command)
            if await proc.wait() != 0:
                await self.notify_error("wallpaper post_command failed")

    async def main_loop(self) -> None:
        """Run the main plugin loop in the 'background'."""
        self.proc = []

        while self.running:
            if not self._paused:
                self.next_background_event.clear()
                await self.terminate()
                variables = state.variables.copy()
                await self._iter_one(variables)

            interval = asyncio.sleep(60 * self.config.get("interval", 10))
            await asyncio.wait(
                [
                    asyncio.create_task(interval),
                    asyncio.create_task(self.next_background_event.wait()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )

    async def terminate(self) -> None:
        """Exit existing process if any."""
        if self.proc:
            for proc in self.proc:
                if proc.returncode is None:
                    proc.terminate()
                await proc.wait()
        self.proc[:] = []

    async def run_wall(self, arg: str) -> None:
        """<next|clear> skip the current background image or stop displaying it."""
        if arg.startswith("n"):  # next
            self._paused = False
            self.next_background_event.set()
        elif arg.startswith("p"):  # pause
            self._paused = True
        elif arg.startswith("cl"):  # clear
            self._paused = True
            await self.terminate()
            clear_command = self.config.get("clear_command")
            if clear_command:
                proc = await asyncio.create_subprocess_shell(clear_command)
                await proc.wait()
        elif arg.startswith("co"):  # color
            # expect an #rgb color code
            args = arg.split()
            color = args[1]
            with contextlib.suppress(IndexError):
                self.config["color_scheme"] = args[2]

            await self._generate_templates("color-" + color, color)
