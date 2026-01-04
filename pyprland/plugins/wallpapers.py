"""Plugin template."""

import asyncio
import colorsys
import contextlib
import os
import os.path
import random
import re
from collections.abc import Callable
from typing import Any, cast

from ..aioops import aiexists, aiopen
from ..common import apply_variables, prepare_for_quotes, state
from .interface import Plugin
from .wallpapers_imageutils import (
    MonitorInfo,
    RoundedImageManager,
    expand_path,
    get_files_with_ext,
    get_variant_color,
    to_hex,
    to_rgb,
    to_rgba,
)
from .wallpapers_utils import can_edit_image, get_dominant_colors, nicify_oklab

HEX_LEN = 6
HEX_LEN_HASH = 7

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


async def fetch_monitors(extension: "Extension") -> list[MonitorInfo]:
    """Fetch monitor information from hyprctl."""
    monitors = await extension.hyprctl_json("monitors")
    return [
        MonitorInfo(name=m["name"], width=int(m["width"]), height=int(m["height"]), transform=m["transform"], scale=m["scale"])
        for m in monitors
    ]


class Extension(Plugin):
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

    async def on_reload(self) -> None:
        """Re-build the image list."""
        cfg_path = self.config["path"]
        paths = [expand_path(cfg_path)] if isinstance(cfg_path, str) else [expand_path(p) for p in cfg_path]
        extensions = self.config.get("extensions", self.default_image_ext)
        radius = int(self.config.get("radius", 0))

        self.image_list = [
            os.path.join(path, fname)
            for path in paths
            async for fname in get_files_with_ext(path, extensions, recurse=self.config.get_bool("recurse"))
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
        elif color_scheme == "vibrant":
            oklab_args = {
                "min_sat": 0.5,
                "max_sat": 0.8,
                "min_light": 0.4,
                "max_light": 0.85,
            }
        elif color_scheme == "mellow":
            oklab_args = {
                "min_sat": 0.3,
                "max_sat": 0.5,
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

    def _generate_palette(  # noqa: PLR0915
        self,
        rgb_list: list[tuple[int, int, int]],
        process_color: Callable[[tuple[int, int, int]], tuple[float, float, float]],
        theme: str = "dark",
    ) -> dict[str, str]:
        """Generate a material-like palette from a single color."""
        hue, light, sat = process_color(rgb_list[0])

        if self.config.get("variant") == "islands":
            h_sec, _, s_sec = process_color(rgb_list[1])
            h_tert, _, s_tert = process_color(rgb_list[2])
        else:
            h_sec, s_sec = hue, sat
            h_tert, s_tert = hue, sat

        colors = {"scheme": theme}

        for name, (h_off, s_mult, l_dark, l_light) in MATERIAL_VARIATIONS.items():
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

            cur_h = (
                float(used_off[1:])
                if isinstance(used_off, str) and used_off.startswith("=")
                else (used_h + float(cast("float", used_off))) % 1.0
            )
            cur_s = max(0.0, min(1.0, used_s * s_mult))

            # Handle source special case
            if l_dark == "source":
                r_dark, g_dark, b_dark = colorsys.hls_to_rgb(hue, light, sat)
                r_dark, g_dark, b_dark = int(r_dark * 255), int(g_dark * 255), int(b_dark * 255)
            else:
                r_dark, g_dark, b_dark = get_variant_color(cur_h, cur_s, float(cast("str", l_dark)))

            if l_light == "source":
                r_light, g_light, b_light = colorsys.hls_to_rgb(hue, light, sat)
                r_light, g_light, b_light = int(r_light * 255), int(g_light * 255), int(b_light * 255)
            else:
                r_light, g_light, b_light = get_variant_color(cur_h, cur_s, float(cast("str", l_light)))

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
        tag_pattern = re.compile(r"\{\{\s*([\w\.]+)(?:\s*\|\s*([\w_]+)\s*(?:[:\s])\s*([^}]+))?\s*\}\}")

        def replace_tag(match: re.Match) -> str:
            key = match.group(1)
            filter_name = match.group(2)
            filter_arg = match.group(3)

            value = replacements.get(key)
            if value is None:
                return cast("str", match.group(0))

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

    async def _process_single_template(
        self,
        name: str,
        template_config: dict[str, str],
        replacements: dict[str, str],
    ) -> None:
        """Process a single template."""
        if "input_path" not in template_config or "output_path" not in template_config:
            self.log.error("Template %s missing input_path or output_path", name)
            return

        input_path = expand_path(template_config["input_path"])
        output_path = expand_path(template_config["output_path"])

        if not await aiexists(input_path):
            self.log.error("Template input file %s not found", input_path)
            return

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
            dominant_colors = await asyncio.to_thread(get_dominant_colors, img_path=img_path)
        theme = await self._detect_theme()

        def process_color(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
            # reduce blue level for earth
            if self.config.get("color_scheme") == "earth":
                rgb = (rgb[0], rgb[1], int(rgb[2] * 0.7))

            r, g, b = nicify_oklab(rgb, **self._get_color_scheme_props())
            return colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)

        replacements = self._generate_palette(dominant_colors, theme=theme, process_color=process_color)
        replacements["image"] = img_path

        for name, template_config in templates.items():
            self.log.debug("processing %s", name)
            await self._process_single_template(name, template_config, replacements)

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
                command_collector.append(apply_variables("wallpaper [output], [file]", variables))

            for cmd in command_collector:
                await self.hyprctl(["execr hyprctl hyprpaper " + cmd])

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
        """<next|clear|pause|color> skip, stop, pause or change color of background."""
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
