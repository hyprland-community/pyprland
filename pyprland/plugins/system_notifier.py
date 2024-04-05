" Add system notifications based on journal logs "
import re
import asyncio
from typing import cast
from copy import deepcopy
from .interface import Plugin
from ..common import apply_filter
from ..adapters.colors import convert_color

builtin_parsers = {
    "journal": [
        {
            "pattern": r"([a-z0-9]+): Link UP$",
            "filter": r"s/.*\[\d+\]: ([a-z0-9]+): Link.*/\1 is active/",
            "color": "#00aa00",
        },
        {
            "pattern": r"([a-z0-9]+): Link DOWN$",
            "filter": r"s/.*\[\d+\]: ([a-z0-9]+): Link.*/\1 is inactive/",
            "color": "#ff8800",
        },
        {
            "pattern": r"Process \d+ \(.*\) of .* dumped core.$",
            "filter": r"s/.*Process \d+ \((.*)\) of .* dumped core./\1 dumped core/",
            "color": "#aa0000",
        },
        {
            "pattern": r"usb \d+-[0-9.]+: Product: ",
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

        for props in self.config.get("sources", []):
            assert (
                props["parser"] in self.parsers
            ), f"{props['parser']} was not found in {self.parsers}"
            self.log.debug("Loaded source %s => %s", props["command"], props["parser"])
            self.tasks.append(asyncio.create_task(self.start_source(props)))

    async def exit(self):
        "empty exit function"
        self.running = False
        for task in self.tasks:
            task.cancel()
            await task
        for source in self.sources.values():
            if source.pid is not None:
                source.kill()
        self.tasks[:] = []

    async def start_source(self, props):
        "Start a source loop"

        parsers = (
            [props["parser"]] if isinstance(props["parser"], str) else props["parser"]
        )
        queues = [self.parsers[p] for p in parsers]
        proc = await asyncio.create_subprocess_shell(
            props["command"], stdout=asyncio.subprocess.PIPE
        )

        self.sources[props["command"]] = proc
        assert proc.stdout
        await asyncio.sleep(1)
        # Read stdout line by line and push to parser
        while proc.returncode is None and self.running:
            line = (await proc.stdout.readline()).decode().strip()
            if line:
                for q in queues:
                    await q.put(line)

    async def start_parser(self, name, props: list):
        "Start a parser loop"
        q = self.parsers[name]
        rules = []
        default_color = self.config.get("default_color", "#5555AA")
        for prop in props:
            rules.append(
                {
                    "pattern": re.compile(prop["pattern"]),
                    "filter": prop.get("filter"),
                    "color": convert_color(prop.get("color", default_color)),
                }
            )
        while self.running:
            content = await q.get()
            for rule in rules:
                if rule["pattern"].search(content):
                    if rule["filter"]:
                        text = apply_filter(content, cast(str, rule["filter"]))
                    else:
                        text = content
                    await self.notify(text, color=rule["color"])
                    await asyncio.sleep(0.01)
