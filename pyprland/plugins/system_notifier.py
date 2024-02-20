" Add system notifications based on journal logs "
import re
import asyncio
from typing import cast
from copy import deepcopy
from .interface import Plugin
from ..common import apply_filter

builtin_parsers = {
    "journal": [
        {
            "pattern": r".*systemd-networkd\[\d+\]: ([a-z0-9]+): Link (UP|DOWN)$",
            "filter": r"s/.*\[\d+\]: ([a-z0-9]+): Link (UP|DOWN)/\1 is \2/",
        },
        {
            "pattern": r".*systemd-coredump\[\d+\]: .* Process \d+ \(([^)])\) of .* dumped core.$",
            "filter": r"s/.*Process \d+ \(([^)])\) of .* dumped core./\1 dumped core/",
        },
        {
            "pattern": r".*usb \d+-[0-9.]+: Product: (.*)",
            "filter": r"s/.*usb \d+-[0-9.]+: Product: (.*)/USB plugged: \1/",
        },
    ]
}


class Extension(Plugin):
    "The plugin code"

    def __init__(self, name):
        super().__init__(name)
        self.tasks: list[asyncio.Task] = []
        self.sources = {}
        self.parsers = {}
        self.running = True

    async def on_reload(self):
        await self.exit()
        self.running = True
        parsers = deepcopy(builtin_parsers)
        parsers.update(self.config.get("parsers", {}))
        for name, pprops in parsers.items():
            self.tasks.append(asyncio.create_task(self.start_parser(name, pprops)))
            self.parsers[name] = asyncio.Queue()
            self.log.debug("Loaded parser %s", name)

        for name, props in self.config.get("source", {}).items():
            assert (
                props["parser"] in self.parsers
            ), f"{props['parser']} was not found in {self.parsers}"
            self.log.debug("Loaded source %s", name)
            self.tasks.append(asyncio.create_task(self.start_source(name, props)))

    async def exit(self):
        "empty exit function"
        self.running = False
        for task in self.tasks:
            task.cancel()
            await task
        self.tasks[:] = []

    async def start_source(self, name, props):
        "Start a source loop"
        q = self.parsers[props["parser"]]
        proc = await asyncio.create_subprocess_shell(
            props["command"], stdout=asyncio.subprocess.PIPE
        )
        self.sources[name] = proc
        assert proc.stdout
        # Read stdout line by line and push to parser
        while self.running:
            line = (await proc.stdout.readline()).decode().strip()
            if line:
                await q.put(line)

    async def start_parser(self, name, props: list):
        "Start a parser loop"
        q = self.parsers[name]
        rules = {}
        for prop in props:
            rules["pattern"] = re.compile(prop["pattern"])
            rules["filter"] = prop["filter"]
        while self.running:
            content = await q.get()
            for prop in rules:
                if rules["pattern"].match(content):
                    if "filter" in rules:
                        text = apply_filter(content, cast(str, rules["filter"]))
                    else:
                        text = content
                    await self.notify(text)
