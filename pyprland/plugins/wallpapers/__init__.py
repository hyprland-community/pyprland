"""Plugin template."""

import asyncio
import colorsys
import contextlib
import os
import os.path
import random
from typing import Any

from ...common import apply_variables, prepare_for_quotes
from ..interface import Plugin
from .colorutils import can_edit_image, get_dominant_colors, nicify_oklab
from .imageutils import (
    MonitorInfo,
    RoundedImageManager,
    expand_path,
    get_files_with_ext,
)
from .templates import TemplateEngine
from .theme import detect_theme, generate_palette, get_color_scheme_props


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
    template_engine: TemplateEngine

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
            return prepare_for_quotes(img_path)

        processed = self.rounded_manager.scale_and_round(img_path, monitor)
        return prepare_for_quotes(processed)

    async def _run_one(self, template: str, values: dict[str, str]) -> None:
        """Run one command."""
        cmd = apply_variables(template, values)
        self.log.info("Running %s", cmd)
        self.proc.append(await asyncio.create_subprocess_shell(cmd))

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
        theme = await detect_theme()

        def process_color(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
            # reduce blue level for earth
            if self.config.get("color_scheme") == "earth":
                rgb = (rgb[0], rgb[1], int(rgb[2] * 0.7))

            color_scheme = self.config.get("color_scheme", "")
            r, g, b = nicify_oklab(rgb, **get_color_scheme_props(color_scheme))
            return colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)

        replacements = generate_palette(
            dominant_colors,
            theme=theme,
            process_color=process_color,
            variant_type=self.config.get("variant"),
        )
        replacements["image"] = img_path

        for name, template_config in templates.items():
            self.log.debug("processing %s", name)
            await self.template_engine.process_single_template(name, template_config, replacements)

    async def update_vars(self, variables: dict[str, Any], monitor: MonitorInfo, img_path: str) -> dict[str, Any]:
        """Get fresh variables for the given monitor."""
        unique = self.config.get("unique", False)
        if unique:
            img_path = self.select_next_image()
        filename = await self._prepare_wallpaper(monitor, img_path)
        variables.update({"file": filename, "output": monitor.name})
        return variables

    async def _iter_one(self, variables: dict[str, Any]) -> None:
        """Run one iteration of the wallpaper loop."""
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
                variables = self.state.variables.copy()
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
