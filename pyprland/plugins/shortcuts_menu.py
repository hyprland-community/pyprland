" Shortcuts menu "
import asyncio

from .interface import Plugin
from ..adapters.menus import MenuRequiredMixin


class Extension(Plugin, MenuRequiredMixin):
    "Shows a menu with shortcuts"

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
