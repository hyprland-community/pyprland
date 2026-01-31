"""Add system notifications based on journal logs."""

import asyncio
import re
from copy import deepcopy
from typing import Any, cast

from ..adapters.colors import convert_color
from ..aioops import TaskManager
from ..common import apply_filter, notify_send
from ..process import ManagedProcess
from ..validation import ConfigField, ConfigItems
from .interface import Plugin

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
    """Opens streams (eg: journal logs) and triggers notifications."""

    config_schema = ConfigItems(
        ConfigField(
            "command",
            dict,
            default={},
            description="""This is the long-running command (eg: `tail -f <filename>`) returning the stream of text that will be updated.
            A common option is the system journal output (eg: `journalctl -u nginx`)""",
            recommended=True,
            category="basic",
        ),
        ConfigField(
            "parser",
            dict,
            default={},
            description="""Sets the list of rules / parser to be used to extract lines of interest
            Must match a list of rules defined as `system_notifier.parsers.<parser_name>`.""",
            category="basic",
        ),
        ConfigField(
            "parsers",
            dict,
            default={},
            description="""Custom parser definitions (name -> list of rules).
            Each rule has: pattern (required), filter, color (defaults to default_color), duration (defaults to 3 seconds)""",
            recommended=True,
            category="parsers",
        ),
        ConfigField(
            "sources", list, default=[], description="Source definitions with command and parser", recommended=True, category="basic"
        ),
        ConfigField(
            "pattern",
            str,
            default="",
            description="The pattern is any regular expression that should trigger a match.",
            recommended=True,
            category="basic",
        ),
        ConfigField("default_color", str, default="#5555AA", description="Default notification color", category="appearance"),
        ConfigField(
            "use_notify_send", bool, default=False, description="Use notify-send instead of Hyprland notifications", category="behavior"
        ),
    )

    _tasks: TaskManager
    sources: dict[str, ManagedProcess]
    parsers: dict[str, asyncio.Queue[Any]]

    def __init__(self, name: str) -> None:
        """Initialize the class."""
        super().__init__(name)
        self._tasks = TaskManager()
        self.sources = {}
        self.parsers = {}

    async def on_reload(self) -> None:
        """Reload the plugin."""
        await self.exit()
        self._tasks.start()
        parsers = deepcopy(builtin_parsers)
        parsers.update(self.get_config_dict("parsers"))
        for name, pprops in parsers.items():
            self._tasks.create(self.start_parser(name, pprops))
            self.parsers[name] = asyncio.Queue()
            self.log.debug("Loaded parser %s", name)

        for props in self.get_config_list("sources"):
            assert props["parser"] in self.parsers, f"{props['parser']} was not found in {self.parsers}"
            self.log.debug("Loaded source %s => %s", props["command"], props["parser"])
            self._tasks.create(self.start_source(props))

    async def exit(self) -> None:
        """Exit function."""
        await self._tasks.stop()
        for source in self.sources.values():
            await source.stop()
        self.sources.clear()

    async def start_source(self, props: dict[str, str]) -> None:
        """Start a source loop.

        A source is a command that will be executed and its stdout will be read line by line.

        Args:
            props: A dictionary with the following keys:
                - command: The command to execute.
                - parser: The name of the parser to use.
        """
        parsers = [props["parser"]] if isinstance(props["parser"], str) else props["parser"]
        queues = [self.parsers[p] for p in parsers]
        proc = ManagedProcess()
        await proc.start(props["command"], stdout=asyncio.subprocess.PIPE)

        self.sources[props["command"]] = proc
        await asyncio.sleep(1)
        # Read stdout line by line and push to parser
        async for line in proc.iter_lines():
            if not self._tasks.running:
                break
            if line:
                for q in queues:
                    await q.put(line)

    async def start_parser(self, name: str, props: list) -> None:
        """Start a parser loop.

        Args:
            name: The name of the parser.
            props: A list of dictionaries with the following keys:
                - pattern: A regex pattern to match.
                - filter: A filter to apply to the matched line.
                - color: The color to use in the notification.
        """
        q = self.parsers[name]
        default_color = self.get_config_str("default_color")
        rules = [
            {
                "pattern": re.compile(prop["pattern"]),
                "filter": prop.get("filter"),
                "color": convert_color(prop.get("color", default_color)),
                "duration": prop.get("duration", 3),
            }
            for prop in props
        ]
        while self._tasks.running:
            content = await q.get()
            for rule in rules:
                if rule["pattern"].search(content):
                    text = apply_filter(content, cast("str", rule["filter"])) if rule["filter"] else content
                    if self.get_config_bool("use_notify_send"):
                        await notify_send(text, duration=rule["duration"] * 1000)
                    else:
                        await self.backend.notify(text, color=rule["color"], duration=rule["duration"])

                    await asyncio.sleep(0.01)
