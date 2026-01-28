"""Plugin template."""

import asyncio
import colorsys
import contextlib
import random
from typing import Any

from ...common import apply_variables
from ...process import ManagedProcess
from ...validation import ConfigField, ConfigItems
from ..interface import Plugin
from .colorutils import can_edit_image, get_dominant_colors, nicify_oklab
from .imageutils import (
    MonitorInfo,
    RoundedImageManager,
    expand_path,
    get_files_with_ext,
)
from .palette import generate_sample_palette, hex_to_rgb, palette_to_json, palette_to_terminal
from .templates import TemplateEngine
from .theme import detect_theme, generate_palette, get_color_scheme_props

# Length of a hex color without '#' prefix
HEX_COLOR_LENGTH = 6


async def fetch_monitors(extension: "Extension") -> list[MonitorInfo]:
    """Fetch monitor information from the backend.

    Works with any backend that implements get_monitors().
    """
    monitors = await extension.backend.get_monitors()
    return [
        MonitorInfo(
            name=m["name"],
            width=int(m["width"]),
            height=int(m["height"]),
            transform=m["transform"],
            scale=m["scale"],
        )
        for m in monitors
    ]


class Extension(Plugin):
    """Handles random wallpapers at regular intervals, with support for rounded corners and color scheme generation."""

    config_schema = ConfigItems(
        ConfigField("path", (str, list), required=True, description="Path(s) to wallpaper images or directories"),
        ConfigField("interval", int, default=10, description="Minutes between wallpaper changes"),
        ConfigField("extensions", list, description="File extensions to include (e.g., ['png', 'jpg'])", default=["png", "jpeg", "jpg"]),
        ConfigField("recurse", bool, default=False, description="Recursively search subdirectories"),
        ConfigField("unique", bool, default=False, description="Use different wallpaper per monitor"),
        ConfigField("radius", int, default=0, description="Corner radius for rounded corners"),
        ConfigField("command", str, description="Custom command to set wallpaper ([file] and [output] variables)"),
        ConfigField("post_command", str, description="Command to run after setting wallpaper"),
        ConfigField("clear_command", str, description="Command to run when clearing wallpaper"),
        ConfigField(
            "color_scheme",
            str,
            default="",
            description="Color scheme for palette generation",
            choices=["", "pastel", "fluo", "fluorescent", "vibrant", "mellow", "neutral", "earth"],
        ),
        ConfigField("variant", str, description="Color variant type for palette"),
        ConfigField("templates", dict, description="Template files for color palette generation"),
    )

    image_list: list[str]
    running = True
    proc: list[ManagedProcess]
    loop = None

    next_background_event = asyncio.Event()
    cur_image = ""
    _paused = False

    rounded_manager: RoundedImageManager | None
    template_engine: TemplateEngine

    async def on_reload(self) -> None:
        """Re-build the image list."""
        self.image_list = []
        # Require 'command' when not on Hyprland (hyprpaper default only works there)
        if not self.get_config("command") and self.state.environment != "hyprland":
            self.log.error(
                "'command' config is required for environment '%s' (hyprpaper default only works on Hyprland)",
                self.state.environment,
            )
            return

        cfg_path: str | list[str] = self.get_config("path")  # type: ignore[assignment]
        paths = [expand_path(cfg_path)] if isinstance(cfg_path, str) else [expand_path(p) for p in cfg_path]
        extensions = self.get_config_list("extensions")
        radius = self.get_config_int("radius")

        self.image_list = [
            full_path for path in paths async for full_path in get_files_with_ext(path, extensions, recurse=self.get_config_bool("recurse"))
        ]

        if radius > 0 and can_edit_image:
            self.rounded_manager = RoundedImageManager(radius)
        else:
            self.rounded_manager = None

        self.template_engine = TemplateEngine(self.log)

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

    async def niri_outputschanged(self, _: dict) -> None:
        """When the monitor configuration changes (Niri), set the background."""
        self.next_background_event.set()

    def select_next_image(self) -> str:
        """Return the next image (random is supported for now)."""
        choice = random.choice(self.image_list)
        if choice == self.cur_image:
            choice = random.choice(self.image_list)
        self.cur_image = choice
        return choice

    async def _prepare_wallpaper(self, monitor: MonitorInfo, img_path: str) -> str:
        """Prepare the wallpaper image for the given monitor."""
        if not self.rounded_manager:
            return img_path
        return self.rounded_manager.scale_and_round(img_path, monitor)

    async def _run_one(self, template: str, values: dict[str, str]) -> None:
        """Run one command."""
        cmd = apply_variables(template, values)
        self.log.info("Running %s", cmd)
        proc = ManagedProcess()
        await proc.start(cmd)
        self.proc.append(proc)

    async def _generate_templates(self, img_path: str, color: str | None = None) -> None:
        """Generate templates from the image."""
        templates = self.get_config_dict("templates") if "templates" in self.config else None
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
        theme = await detect_theme(self.log)

        def process_color(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
            # reduce blue level for earth
            color_scheme = self.get_config_str("color_scheme")
            if color_scheme == "earth":
                rgb = (rgb[0], rgb[1], int(rgb[2] * 0.7))

            r, g, b = nicify_oklab(rgb, **get_color_scheme_props(color_scheme))
            return colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)

        variant = self.get_config_str("variant") or None
        replacements = generate_palette(
            dominant_colors,
            theme=theme,
            process_color=process_color,
            variant_type=variant,
        )
        replacements["image"] = img_path

        for name, template_config in templates.items():
            self.log.debug("processing %s", name)
            await self.template_engine.process_single_template(name, template_config, replacements)

    async def update_vars(self, variables: dict[str, Any], monitor: MonitorInfo, img_path: str) -> dict[str, Any]:
        """Get fresh variables for the given monitor."""
        if self.get_config_bool("unique"):
            img_path = self.select_next_image()
        filename = await self._prepare_wallpaper(monitor, img_path)
        variables.update({"file": filename, "output": monitor.name})
        return variables

    async def _iter_one(self, variables: dict[str, Any]) -> None:
        """Run one iteration of the wallpaper loop."""
        cmd_template = self.get_config("command")
        assert isinstance(cmd_template, str) or cmd_template is None
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
                await self.backend.execute(["execr hyprctl hyprpaper " + cmd])

        # Generate templates after wallpaper is selected
        await self._generate_templates(img_path)

        # check if the command failed
        for proc in self.proc:
            if proc.returncode:
                await self.backend.notify_error("wallpaper command failed")
                break

        post_command = self.get_config_str("post_command")
        if post_command:
            command = apply_variables(post_command, variables)
            post_proc = await asyncio.create_subprocess_shell(command)
            if await post_proc.wait() != 0:
                await self.backend.notify_error("wallpaper post_command failed")

    async def main_loop(self) -> None:
        """Run the main plugin loop in the 'background'."""
        self.proc = []

        while self.running:
            if not self._paused:
                self.next_background_event.clear()
                await self.terminate()
                variables = self.state.variables.copy()
                await self._iter_one(variables)

            interval_minutes = self.get_config_float("interval")
            interval = asyncio.sleep(60 * interval_minutes)
            await asyncio.wait(
                [
                    asyncio.create_task(interval),
                    asyncio.create_task(self.next_background_event.wait()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )

    async def terminate(self) -> None:
        """Exit existing process if any."""
        for proc in self.proc:
            await proc.stop()
        self.proc.clear()

    async def run_wall(self, arg: str) -> None:
        """<next|pause|clear> Control wallpaper cycling."""
        if arg.startswith("n"):  # next
            self._paused = False
            self.next_background_event.set()
        elif arg.startswith("p"):  # pause
            self._paused = True
        elif arg.startswith("cl"):  # clear
            self._paused = True
            await self.terminate()
            if not self.get_config("command") and self.state.environment == "hyprland":
                pkill_proc = await asyncio.create_subprocess_shell("pkill hyprpaper")
                await pkill_proc.wait()
            clear_command = self.get_config_str("clear_command")
            if clear_command:
                clear_proc = await asyncio.create_subprocess_shell(clear_command)
                await clear_proc.wait()

    async def run_color(self, arg: str) -> None:
        """<#RRGGBB> [scheme] Generate color palette from hex color."""
        args = arg.split()
        color = args[0]
        with contextlib.suppress(IndexError):
            self.config["color_scheme"] = args[1]

        await self._generate_templates("color-" + color, color)

    async def run_palette(self, arg: str = "") -> str:
        """[color] [json] Show available color template variables."""
        args = arg.split()
        color: str | None = None
        output_json = False

        # Parse arguments: [color] [json]
        for a in args:
            if a.lower() == "json":
                output_json = True
            elif a.startswith("#") or (len(a) == HEX_COLOR_LENGTH and all(c in "0123456789abcdefABCDEF" for c in a)):
                color = a

        # Determine base RGB color
        if color:
            base_rgb = hex_to_rgb(color)
        elif self.cur_image and can_edit_image:
            # Use colors from current wallpaper
            dominant_colors = await asyncio.to_thread(get_dominant_colors, img_path=self.cur_image)
            base_rgb = dominant_colors[0]
        else:
            # Default: Google blue #4285F4
            base_rgb = (66, 133, 244)

        theme = await detect_theme(self.log)
        palette = generate_sample_palette(base_rgb, theme)

        if output_json:
            return palette_to_json(palette)
        return palette_to_terminal(palette)
