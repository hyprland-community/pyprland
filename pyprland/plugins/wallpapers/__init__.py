"""Plugin template."""

import asyncio
import colorsys
import contextlib
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ...aioops import TaskManager, aiexists, airmdir, airmtree
from ...common import apply_variables
from ...constants import (
    DEFAULT_PALETTE_COLOR_RGB,
    DEFAULT_WALLPAPER_HEIGHT,
    DEFAULT_WALLPAPER_WIDTH,
    PREFETCH_MAX_RETRIES,
    PREFETCH_RETRY_BASE_SECONDS,
    PREFETCH_RETRY_MAX_SECONDS,
    SECONDS_PER_DAY,
)
from ...process import ManagedProcess
from ...validation import ConfigField, ConfigItems
from ..interface import Plugin
from .cache import ImageCache
from .colorutils import can_edit_image, get_dominant_colors, nicify_oklab
from .imageutils import (
    MonitorInfo,
    RoundedImageManager,
    expand_path,
    get_files_with_ext,
)
from .online import NoBackendAvailableError, OnlineFetcher
from .palette import generate_sample_palette, hex_to_rgb, palette_to_json, palette_to_terminal
from .templates import TemplateEngine
from .theme import detect_theme, generate_palette, get_color_scheme_props

# Length of a hex color without '#' prefix
HEX_COLOR_LENGTH = 6

# Default backends that support size filtering (excludes bing which returns fixed 1920x1080)
DEFAULT_ONLINE_BACKENDS = ["unsplash", "picsum", "wallhaven", "reddit"]


@dataclass
class OnlineState:
    """State for online wallpaper fetching."""

    fetcher: OnlineFetcher | None = None
    folder_path: Path | None = None
    cache: ImageCache | None = None
    rounded_cache: ImageCache | None = None
    prefetched_path: str | None = None


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
        # Online wallpaper fetching options
        ConfigField("online_ratio", float, default=0.0, description="Probability of fetching online (0.0-1.0)"),
        ConfigField(
            "online_backends",
            list,
            default=DEFAULT_ONLINE_BACKENDS,
            description="Enabled online backends",
        ),
        ConfigField("online_keywords", list, default=[], description="Keywords to filter online images"),
        ConfigField("online_folder", str, default="online", description="Subfolder for downloaded online images"),
        # Cache options
        ConfigField("cache_days", int, default=0, description="Days to keep cached images (0 = forever)"),
        ConfigField("cache_max_mb", int, default=100, description="Maximum cache size in MB (0 = unlimited)"),
        ConfigField("cache_max_images", int, default=0, description="Maximum number of cached images (0 = unlimited)"),
    )

    image_list: list[str]
    _tasks: TaskManager
    _loop_started = False
    proc: list[ManagedProcess]

    next_background_event = asyncio.Event()
    cur_image = ""
    _paused = False

    rounded_manager: RoundedImageManager | None
    template_engine: TemplateEngine

    # Online fetching state
    _online: OnlineState | None = None

    def __init__(self, name: str) -> None:
        """Initialize the plugin."""
        super().__init__(name)
        self._tasks = TaskManager()

    async def on_reload(self) -> None:
        """Re-build the image list."""
        # Clean up legacy cache folder if it exists
        legacy_cache = Path.home() / ".cache" / "pyprland" / "wallpapers"
        if await aiexists(legacy_cache):
            await airmtree(str(legacy_cache))
            self.log.info("Removed legacy cache folder: %s", legacy_cache)
            # Also remove parent if empty
            parent = legacy_cache.parent
            if await aiexists(parent) and not any(parent.iterdir()):
                await airmdir(str(parent))

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
        online_ratio = self.get_config_float("online_ratio")

        # Build local image list
        self.image_list = [
            full_path for path in paths async for full_path in get_files_with_ext(path, extensions, recurse=self.get_config_bool("recurse"))
        ]

        # Set up online fetching and get rounded cache
        self._online = await self._setup_online_fetching(paths, extensions, online_ratio)

        # Warn if no local images but online_ratio < 1
        if not self.image_list and online_ratio < 1.0:
            await self._warn_no_images()

        # Set up rounded corners manager with appropriate cache location
        rounded_cache = self._online.rounded_cache if self._online else None
        if radius > 0 and can_edit_image:
            if not rounded_cache:
                # Create local rounded cache when online is disabled
                first_path = paths[0] if paths else expand_path("~/Pictures/Wallpapers")
                rounded_cache_dir = Path(first_path) / "rounded"
                rounded_cache_dir.mkdir(parents=True, exist_ok=True)
                rounded_cache = self._create_cache(rounded_cache_dir)
            self.rounded_manager = RoundedImageManager(radius, cache=rounded_cache)
        else:
            self.rounded_manager = None

        self.template_engine = TemplateEngine(self.log)

        # Clean up expired cache entries asynchronously
        await self._cleanup_caches()

        # Start the main loop if it's the first load of the config
        if not self._loop_started:
            self._tasks.start()
            self._tasks.create(self.main_loop())
            self._loop_started = True

    def _create_cache(self, cache_dir: Path) -> ImageCache:
        """Create an ImageCache with the configured TTL and size limits."""
        cache_days = self.get_config_int("cache_days")
        cache_max_mb = self.get_config_int("cache_max_mb")
        return ImageCache(
            cache_dir=cache_dir,
            ttl=cache_days * SECONDS_PER_DAY if cache_days else None,
            max_size=cache_max_mb * 1024 * 1024 if cache_max_mb else None,
            max_count=self.get_config_int("cache_max_images") or None,
        )

    async def _setup_online_fetching(
        self,
        paths: list[str],
        extensions: list[str],
        online_ratio: float,
    ) -> OnlineState | None:
        """Set up online fetching if enabled.

        Args:
            paths: List of wallpaper paths.
            extensions: List of file extensions.
            online_ratio: Probability of fetching online.

        Returns:
            OnlineState with fetcher and caches, or None if online disabled.
        """
        # Close existing fetcher if any
        if self._online and self._online.fetcher:
            await self._online.fetcher.close()

        if online_ratio <= 0:
            return None

        # Set up online folder
        first_path = paths[0] if paths else expand_path("~/Pictures/Wallpapers")
        online_folder_name = self.get_config_str("online_folder") or "online"
        folder_path = Path(first_path) / online_folder_name
        folder_path.mkdir(parents=True, exist_ok=True)

        # Create online cache
        online_cache = self._create_cache(folder_path)

        # Create rounded cache subfolder and cache
        rounded_cache_dir = folder_path / "rounded"
        rounded_cache_dir.mkdir(parents=True, exist_ok=True)
        rounded_cache = self._create_cache(rounded_cache_dir)

        # Initialize OnlineFetcher with the online cache
        backends = self.get_config_list("online_backends")
        fetcher: OnlineFetcher | None = None
        try:
            fetcher = OnlineFetcher(
                backends=backends or None,
                cache=online_cache,
                log=self.log,
            )
            self.log.info("Online fetching enabled with backends: %s", fetcher.backends)
        except ValueError:
            self.log.exception("Failed to initialize online fetcher")

        # Always scan online folder for existing images (regardless of recurse setting)
        async for full_path in get_files_with_ext(str(folder_path), extensions, recurse=False):
            if full_path not in self.image_list:
                self.image_list.append(full_path)

        return OnlineState(
            fetcher=fetcher,
            folder_path=folder_path,
            cache=online_cache,
            rounded_cache=rounded_cache,
        )

    async def _cleanup_caches(self) -> None:
        """Clean up expired cache entries asynchronously."""
        cache_days = self.get_config_int("cache_days")
        if not cache_days or not self._online:
            return  # No TTL configured or online disabled, skip cleanup

        cleanup_tasks = []
        if self._online.cache:
            cleanup_tasks.append(asyncio.to_thread(self._online.cache.cleanup))
        if self._online.rounded_cache:
            cleanup_tasks.append(asyncio.to_thread(self._online.rounded_cache.cleanup))

        if cleanup_tasks:
            results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            total_removed = sum(r for r in results if isinstance(r, int))
            if total_removed > 0:
                self.log.info("Cache cleanup: removed %d expired files", total_removed)

    async def _warn_no_images(self) -> None:
        """Warn user when no local images are available."""
        if self._online and self._online.fetcher:
            self.log.warning("No local images found, will use online-only mode")
            await self.backend.notify_info("No local wallpapers found, using online only")
        else:
            self.log.error("No images available: no local images and online fetching disabled")
            await self.backend.notify_error("No wallpapers available")

    async def exit(self) -> None:
        """Terminates gracefully."""
        await self._tasks.stop()
        self._loop_started = False
        await self.terminate()

        # Close online fetcher session
        if self._online and self._online.fetcher:
            await self._online.fetcher.close()

    async def event_monitoradded(self, _: str) -> None:
        """When a new monitor is added, set the background."""
        self.next_background_event.set()

    async def niri_outputschanged(self, _: dict) -> None:
        """When the monitor configuration changes (Niri), set the background."""
        self.next_background_event.set()

    async def select_next_image(self) -> str:
        """Return the next image - randomly selects online or local based on ratio."""
        online_ratio = self.get_config_float("online_ratio")
        use_online = random.random() < online_ratio
        has_online_fetcher = self._online is not None and self._online.fetcher is not None

        # Fallback logic
        if use_online and not has_online_fetcher:
            use_online = False
        if not use_online and not self.image_list:
            if has_online_fetcher:
                use_online = True
            else:
                self.log.error("No images available (local or online)")
                return self.cur_image  # Return current or empty

        if use_online:
            choice = await self._fetch_online_image()
        else:
            choice = random.choice(self.image_list)
            if choice == self.cur_image and len(self.image_list) > 1:
                choice = random.choice(self.image_list)

        self.cur_image = choice
        return choice

    async def _fetch_online_image(self) -> str:
        """Fetch a new image from online backends.

        Uses prefetched image if available, otherwise fetches synchronously.

        Returns:
            Path to the downloaded image.

        Raises:
            NoBackendAvailableError: If all backends fail and no local fallback.
        """
        # Use prefetched image if available
        if self._online and self._online.prefetched_path:
            path = self._online.prefetched_path
            self._online.prefetched_path = None
            if await aiexists(path):
                self.log.debug("Using prefetched image: %s", path)
                return path
            self.log.debug("Prefetched image no longer exists, fetching new")

        if not self._online or not self._online.fetcher:
            msg = "Online fetcher not initialized"
            raise RuntimeError(msg)

        fetcher = self._online.fetcher

        # Get monitor dimensions for size hint
        monitors = await fetch_monitors(self)
        max_width = max((m.width for m in monitors), default=DEFAULT_WALLPAPER_WIDTH)
        max_height = max((m.height for m in monitors), default=DEFAULT_WALLPAPER_HEIGHT)

        keywords = self.get_config_list("online_keywords") or None

        try:
            path = str(
                await fetcher.get_image(
                    min_width=max_width,
                    min_height=max_height,
                    keywords=keywords,
                )
            )
        except NoBackendAvailableError:
            self.log.exception("Failed to fetch online image")
            await self.backend.notify_error("Online wallpaper fetch failed")

            # Fallback to local if available
            if self.image_list:
                return random.choice(self.image_list)
            raise

        # Add to local pool for future selection
        if path not in self.image_list:
            self.image_list.append(path)

        return path

    async def _prefetch_online_image(self) -> None:
        """Prefetch next online image in background with exponential backoff retry."""
        if not self._online or not self._online.fetcher:
            return

        monitors = await fetch_monitors(self)
        max_width = max((m.width for m in monitors), default=DEFAULT_WALLPAPER_WIDTH)
        max_height = max((m.height for m in monitors), default=DEFAULT_WALLPAPER_HEIGHT)
        keywords = self.get_config_list("online_keywords") or None

        for attempt in range(PREFETCH_MAX_RETRIES):
            try:
                path = await self._online.fetcher.get_image(min_width=max_width, min_height=max_height, keywords=keywords)
                self._online.prefetched_path = str(path)
                if str(path) not in self.image_list:
                    self.image_list.append(str(path))
                self.log.debug("Prefetched: %s", path)
            except Exception:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                # Catch all errors (network, parsing, etc.) to retry with different backend
                if attempt < PREFETCH_MAX_RETRIES - 1:
                    delay = min(PREFETCH_RETRY_BASE_SECONDS * (2**attempt), PREFETCH_RETRY_MAX_SECONDS)
                    self.log.debug("Prefetch attempt %d failed, retry in %ds", attempt + 1, delay)
                    await asyncio.sleep(delay)
            else:
                return

        self.log.warning("Prefetch failed after %d retries", PREFETCH_MAX_RETRIES)

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
            img_path = await self.select_next_image()
        filename = await self._prepare_wallpaper(monitor, img_path)
        variables.update({"file": filename, "output": monitor.name})
        return variables

    async def _iter_one(self, variables: dict[str, Any]) -> None:
        """Run one iteration of the wallpaper loop."""
        cmd_template = self.get_config("command")
        assert isinstance(cmd_template, str) or cmd_template is None
        img_path = await self.select_next_image()
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

        # Prefetch next online image if enabled and previous was consumed
        if self._online and self._online.fetcher and not self._online.prefetched_path:
            self._tasks.create(self._prefetch_online_image())

    async def main_loop(self) -> None:
        """Run the main plugin loop in the 'background'."""
        self.proc = []

        while self._tasks.running:
            if not self._paused:
                self.next_background_event.clear()
                await self.terminate()
                variables = self.state.variables.copy()
                await self._iter_one(variables)

            interval_minutes = self.get_config_float("interval")
            sleep_task = asyncio.create_task(asyncio.sleep(60 * interval_minutes))
            event_task = asyncio.create_task(self.next_background_event.wait())
            _, pending = await asyncio.wait(
                [sleep_task, event_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            # Cancel pending tasks to avoid leaks
            for task in pending:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    async def terminate(self) -> None:
        """Exit existing process if any."""
        for proc in self.proc:
            await proc.stop()
        self.proc.clear()

    async def run_wall(self, arg: str) -> None:
        """<next|pause|clear> Control wallpaper cycling.

        Args:
            arg: The action to perform
                - next: Switch to the next wallpaper immediately
                - pause: Pause automatic wallpaper cycling
                - clear: Stop cycling and clear the current wallpaper
        """
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
        """<#RRGGBB> [scheme] Generate color palette from hex color.

        Args:
            arg: Hex color and optional scheme name

        Schemes: pastel, fluo, vibrant, mellow, neutral, earth

        Example:
            pypr color #ff5500 vibrant
        """
        args = arg.split()
        color = args[0]
        with contextlib.suppress(IndexError):
            self.config["color_scheme"] = args[1]

        await self._generate_templates("color-" + color, color)

    async def run_palette(self, arg: str = "") -> str:
        """[color] [json] Show available color template variables.

        Args:
            arg: Optional hex color and/or "json" flag
                - color: Hex color (#RRGGBB) to use for palette
                - json: Output in JSON format instead of human-readable

        Example:
            pypr palette
            pypr palette #ff5500
            pypr palette json
        """
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
            base_rgb = DEFAULT_PALETTE_COLOR_RGB

        theme = await detect_theme(self.log)
        palette = generate_sample_palette(base_rgb, theme)

        if output_json:
            return palette_to_json(palette)
        return palette_to_terminal(palette)
