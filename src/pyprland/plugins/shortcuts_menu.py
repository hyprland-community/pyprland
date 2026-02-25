"""Shortcuts menu."""

import asyncio
from typing import cast

from ..adapters.menus import MenuMixin
from ..common import apply_filter, apply_variables
from ..validation import ConfigField, ConfigItems
from .interface import Plugin


class Extension(MenuMixin, Plugin):
    """A flexible way to make your own shortcuts menus & launchers."""

    config_schema = ConfigItems(
        ConfigField("entries", dict, required=True, description="Menu entries structure (nested dict of commands)", category="basic"),
        *MenuMixin.menu_config_schema,
        ConfigField("separator", str, default=" | ", description="Separator for menu display", category="appearance"),
        ConfigField("command_start", str, default="", description="Prefix for command entries", category="appearance"),
        ConfigField("command_end", str, default="", description="Suffix for command entries", category="appearance"),
        ConfigField("submenu_start", str, default="", description="Prefix for submenu entries", category="appearance"),
        ConfigField("submenu_end", str, default="➜", description="Suffix for submenu entries", category="appearance"),
        ConfigField("skip_single", bool, default=True, description="Auto-select when only one option available", category="behavior"),
    )

    # Commands

    async def run_menu(self, name: str = "") -> None:
        """[name] Shows the menu, if "name" is provided, will only show this sub-menu.

        Args:
            name: The menu name
        """
        await self.ensure_menu_configured()
        options: dict | list | str = self.get_config_dict("entries")
        if name:
            for elt in name.split("."):
                assert isinstance(options, dict), f"Cannot navigate into non-dict at '{elt}'"
                options = options[elt]

        def _format_title(label: str, obj: str | list) -> str:
            if isinstance(obj, str):
                suffix = self.get_config_str("command_end")
                prefix = self.get_config_str("command_start")
            else:
                suffix = self.get_config_str("submenu_end")
                prefix = self.get_config_str("submenu_start")

            return f"{prefix} {label} {suffix}".strip()

        while True:
            selection = name
            if isinstance(options, str):
                self.log.info("running %s", options)
                await self._run_command(options.strip(), self.state.variables)
                break
            if isinstance(options, list):
                self.log.info("interpreting %s", options)
                await self._handle_chain(options)
                break
            try:
                formatted_options = {_format_title(k, v): v for k, v in options.items()}
                if self.get_config_bool("skip_single") and len(formatted_options) == 1:
                    selection = next(iter(formatted_options.keys()))
                else:
                    selection = await self.menu.run(formatted_options, selection)
                options = formatted_options[selection]
            except KeyError:
                self.log.info("menu command canceled")
                break

    # Utils

    async def _handle_chain(self, options: list[str | dict]) -> None:
        """Handle a chain of special objects + final command string.

        Args:
            options: The chain of options
        """
        variables: dict[str, str] = self.state.variables.copy()
        autovalidate = self.get_config_bool("skip_single")
        for option in options:
            if isinstance(option, str):
                await self._run_command(option, variables)
            else:
                choices = []
                var_name = option["name"]
                if option.get("command"):  # use the option to select some variable
                    proc = await asyncio.create_subprocess_shell(option["command"], stdout=asyncio.subprocess.PIPE)
                    assert proc.stdout
                    await proc.wait()
                    option_array = (await proc.stdout.read()).decode().split("\n")
                    choices.extend([apply_variables(line, variables).strip() for line in option_array if line.strip()])
                elif option.get("options"):
                    choices.extend(apply_variables(txt, variables) for txt in option["options"])
                if not choices:
                    await self.backend.notify_info("command didn't return anything")
                    return

                if autovalidate and len(choices) == 1:
                    variables[var_name] = choices[0]
                else:
                    selection = await self.menu.run(choices, var_name)
                    variables[var_name] = apply_filter(selection, cast("str", option.get("filter", "")))
                    self.log.debug("set %s = %s", var_name, variables[var_name])

    async def _run_command(self, command: str, variables: dict[str, str]) -> None:
        """Run a shell `command`, optionally replacing `variables`.

        The command is run in a shell, and the variables are replaced using the `apply_variables` function.

        Args:
            command: The command to run.
            variables: The variables to replace in the command.
        """
        final_command = apply_variables(command, variables)
        self.log.info("Executing %s", final_command)
        await asyncio.create_subprocess_shell(final_command)
