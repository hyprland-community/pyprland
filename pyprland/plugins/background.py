" Plugin template "
import random
import asyncio
import os.path

from aiofiles.os import listdir

from .interface import Plugin


class Extension(Plugin):
    "Manages the background image"

    valid_extensions = set(("png", "jpg", "jpeg"))
    running = True
    image_list: list[str] = []
    proc = None
    loop = None

    next_background_event = asyncio.Event()
    cur_image = ""

    async def on_reload(self):
        "Re-build the image list"
        image_list = []
        cfg_path = self.config["path"]
        paths = [cfg_path] if isinstance(cfg_path, str) else list(cfg_path)
        for path in paths:
            for fname in await listdir(path):
                ext = fname.rsplit(".", 1)[-1]
                if ext.lower() in self.valid_extensions:
                    image_list.append(os.path.join(path, fname))
        self.image_list = image_list
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

    async def main_loop(self):
        "Main plugin loop, runs in the 'background'"
        self.proc = None
        cmd_prefix = self.config.get("command", "swaybg -m fill -i")
        while self.running:
            self.next_background_event.clear()
            filename = self.select_next_image().replace("'", r"""'"'"'""")
            cmd = f"{cmd_prefix} '{filename}'"
            self.log.info("Running %s", cmd)
            self.proc = await asyncio.create_subprocess_shell(cmd)

            interval = asyncio.sleep(60 * self.config.get("interval", 10))
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
            self.proc.terminate()
            await self.proc.wait()
            self.proc = None

    async def run_next_background(self):
        "Changes the current background image"
        self.next_background_event.set()

    async def run_clear_background(self):
        "Clear the current background image"
        await self.terminate()
