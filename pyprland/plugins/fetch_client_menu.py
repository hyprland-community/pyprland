" Select a client window and move it to the active workspace"

from .interface import Plugin
from ..adapters.menus import MenuRequiredMixin
from ..common import state


class Extension(Plugin, MenuRequiredMixin):
    "Shows a menu with shortcuts"

    # Commands

    async def run_fetch_client_menu(self):
        "Select a client window and move it to the active workspace"
        await self._ensure_menu_configured()

        clients = await self.hyprctlJSON("clients")

        options = {
            f"{i} | {c['title']}": c
            for i, c in enumerate(clients)
            if c["mapped"] and c["workspace"]["name"] != state.active_workspace
        }
        choice = await self.menu.run(options.keys())

        if choice in options:
            addr = options[choice]["address"]
            await self.hyprctl(
                f"movetoworkspace {state.active_workspace},address:{addr}"
            )
