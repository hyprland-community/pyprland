" Shortcuts menu "
import asyncio
from asyncio import subprocess

from .interface import Plugin
from ..adapters.menus import MenuRequiredMixin


class Extension(Plugin, MenuRequiredMixin):
    "Shows a menu with shortcuts"

    # Commands

    async def _handle_chain(self, options):
        "Handles a chain of special objects + final command string"
        variables: dict[str, str] = {}
        for option in options:
            if isinstance(option, str):
                await self._run_command(option, variables)
            else:
                choices = []
                var_name = option["var"]
                if option.get("command"):  # use the option to select some variable
                    proc = await asyncio.create_subprocess_shell(
                        option["command"], stdout=subprocess.PIPE
                    )
                    assert proc.stdout
                    await proc.wait()
                    choices.extend(
                        [
                            line.strip()
                            for line in (await proc.stdout.read()).decode().split("\n")
                        ]
                    )
                elif option.get("options"):
                    choices.extend(option["options"])
                variables[var_name] = await self.menu.run(choices)

    async def _run_command(self, command, variables=None):
        "Runs a shell `command`, optionally replacing `variables`"
        self.log.info("Executing %s (%s)", command, variables)
        await asyncio.create_subprocess_shell(
            command.format(**variables) if variables else command
        )

    async def run_menu(self, name=""):
        """[name] Shows the menu, if "name" is provided, will only show this sub-menu"""
        await self.ensure_menu_configured()
        options = self.config["entries"]
        if name:
            options = options[name]

        while True:
            if isinstance(options, str):
                self.log.info("running %s", options)
                await self._run_command(options.strip())
                break
            if isinstance(options, list):
                self.log.info("interpreting %s", options)
                await self._handle_chain(options)
                break
            try:
                options = options[await self.menu.run(options)]
            except KeyError:
                self.log.info("menu command canceled")
                break
