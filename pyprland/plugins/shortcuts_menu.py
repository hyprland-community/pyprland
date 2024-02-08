" Shortcuts menu "
import asyncio

from .interface import Plugin
from ..adapters.menus import init, MenuEngine


class Extension(Plugin):
    "Shows a menu with shortcuts"

    menu: MenuEngine
    _configured = False

    async def on_reload(self):
        self._configured = False

    async def _ensure_configured(self):
        "If not configured, init the menu system"
        if not self._configured:
            self.menu = await init(
                self.config.get("engine"), self.config.get("parameters", "")
            )
            self.log.info("Using %s engine", self.menu.proc_name)
            self._configured = True

    # Commands

    async def run_menu(self, name=""):
        """[name] Shows the menu, if "name" is provided, will only show this sub-menu"""
        await self._ensure_configured()
        options = self.config["entries"]
        if name:
            options = options[name]

        while True:
            if isinstance(options, str):
                self.log.info("running %s", options)
                await asyncio.create_subprocess_shell(options.strip())
                break
            try:
                options = options[await self.menu.run(options)]
            except KeyError:
                self.log.info("menu command canceled")
                break
