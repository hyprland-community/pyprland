"""Plugin template."""

import asyncio
import os
import os.path
import random
from collections.abc import AsyncIterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageOps

    can_edit_image = True
except ImportError:
    can_edit_image = False

from ..aioops import ailistdir
from ..common import CastBoolMixin, apply_variables, prepare_for_quotes, state
from .interface import Plugin

IMAGE_FORMAT = "jpg"
HYPRPAPER_SOCKET = os.path.join(
    os.environ.get("XDG_RUNTIME_DIR", "/run/user/1000"),
    "hypr",
    os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "default"),
    ".hyprpaper.sock",
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
            with Image.open(src) as img:
                is_rotated = monitor.transform % 2
                width, height = (monitor.width, monitor.height) if not is_rotated else (monitor.height, monitor.width)
                width = int(width / monitor.scale)
                height = int(height / monitor.scale)
                resample = Image.Resampling.LANCZOS
                resized = ImageOps.fit(img, (width, height), method=resample)

                scale = 4
                image_width, image_height = resized.width * scale, resized.height * scale
                rounded_mask = Image.new("L", (image_width, image_height), 0)
                corner_draw = ImageDraw.Draw(rounded_mask)
                corner_draw.rounded_rectangle((0, 0, image_width - 1, image_height - 1), radius=self.radius * scale, fill=255)
                mask = rounded_mask.resize(resized.size, resample=resample)

                result = Image.new("RGB", resized.size, "black")
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
        hyprpaper_socket_reader, hyprpaper_socket_writer = await asyncio.open_unix_connection(HYPRPAPER_SOCKET)
        hyprpaper_socket_writer.write(message)
        await hyprpaper_socket_writer.drain()
        hyprpaper_socket_writer.close()

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
                command_collector.append(apply_variables("preload [file]", variables))
                command_collector.append(apply_variables("wallpaper [output], [file]", variables))

            for cmd in command_collector:
                await self._send_hyprpaper(cmd.encode())

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
        elif arg.startswith("c"):  # clear
            self._paused = True
            await self.terminate()
            clear_command = self.config.get("clear_command")
            if clear_command:
                proc = await asyncio.create_subprocess_shell(clear_command)
                await proc.wait()
