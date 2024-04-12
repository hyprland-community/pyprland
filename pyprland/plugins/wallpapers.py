" Plugin template "
import random
import asyncio
import os.path

from aiofiles.os import listdir

from .interface import Plugin
from ..common import CastBoolMixin, apply_variables, state


async def iter_dir(path, extensions, recurse=True):
    "Returns files matching `extension` in given `path`. Can optionally `recurse` subfolders."
    for fname in await listdir(path):
        ext = fname.rsplit(".", 1)[-1]
        full_path = os.path.join(path, fname)
        if ext.lower() in extensions:
            yield full_path
        elif recurse and os.path.isdir(full_path):
            async for v in iter_dir(full_path, extensions, True):
                yield v


class Extension(CastBoolMixin, Plugin):
    "Manages the background image"

    default_extensions: set[str] | list[str] = set(("png", "jpg", "jpeg"))
    image_list: list[str] = []
    running = True
    proc: list = []
    loop = None

    next_background_event = asyncio.Event()
    cur_image = ""

    async def on_reload(self):
        "Re-build the image list"
        image_list = []
        cfg_path = self.config["path"]
        paths = [cfg_path] if isinstance(cfg_path, str) else list(cfg_path)
        extensions = self.config.get("extensions", self.default_extensions)
        for path in paths:
            async for fname in iter_dir(
                path, extensions, recurse=self.cast_bool(self.config.get("recurse"))
            ):
                image_list.append(os.path.join(path, fname))
        self.image_list = image_list
        # start the main loop if it's the first load of the config
        if self.loop is None:
            self.loop = asyncio.create_task(self.main_loop())

    async def exit(self):
        "terminates gracefully"
        self.running = False
        if self.loop:
            self.loop.cancel()
        await self.terminate()

    def select_next_image(self):
        "Returns the next image (random is supported for now)"
        choice = random.choice(self.image_list)
        if choice == self.cur_image:
            choice = random.choice(self.image_list)
        self.cur_image = choice
        return choice

    async def _run_one(self, template, values):
        "Runs one command"
        cmd = apply_variables(template, values)
        self.log.info("Running %s", cmd)
        self.proc.append(await asyncio.create_subprocess_shell(cmd))

    async def main_loop(self):
        "Main plugin loop, runs in the 'background'"
        self.proc = []
        unique = self.config.get("unique", False)
        variables = state.variables.copy()
        while self.running:
            self.next_background_event.clear()
            if unique:
                cmd_template = self.config.get(
                    "command", 'swaybg -o [output] -m fill -i "[file]"'
                )
                monitors = await self.hyprctlJSON("monitors")
                old_filename = None
                for monitor in monitors:
                    filename = self.select_next_image().replace('"', '\\"')
                    while filename == old_filename:
                        filename = self.select_next_image().replace('"', '\\"')
                    variables.update({"file": filename, "output": monitor["name"]})
                    await self._run_one(cmd_template, variables)
            else:
                cmd_template = self.config.get("command", 'swaybg -m fill -i "[file]"')
                filename = self.select_next_image().replace('"', '\\"')
                variables.update({"file": filename})
                await self._run_one(cmd_template, variables)
            await asyncio.sleep(1)  # wait for the command(s) to start
            # check if the command failed
            for proc in self.proc:
                if proc.returncode:
                    await self.notify_error("wallpaper command failed")

            interval = asyncio.sleep(60 * self.config.get("interval", 10) - 1)
            await asyncio.wait(
                [
                    asyncio.create_task(interval),
                    asyncio.create_task(self.next_background_event.wait()),
                ],
                return_when=asyncio.FIRST_COMPLETED,
            )

            await self.terminate()

    async def terminate(self):
        "Exits existing process if any"
        if self.proc:
            for proc in self.proc:
                if proc.returncode is None:
                    proc.terminate()
                await proc.wait()
        self.proc[:] = []

    async def run_wall(self, arg):
        "<next|clear> skip the current background image or stop displaying it"
        if arg.startswith("n"):
            self.next_background_event.set()
        elif arg.startswith("c"):
            clear_command = self.config.get("clear_command")
            if clear_command:
                # call clear_command subprocess
                proc = await asyncio.create_subprocess_shell(clear_command)
                # wait for it to finish
                await proc.wait()
            else:
                await self.terminate()
