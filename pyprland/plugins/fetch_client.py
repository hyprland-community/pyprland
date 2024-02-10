" Select a client window and move it to the active workspace"

from typing import cast

from .interface import Plugin
from ..adapters.menus import MenuRequiredMixin


class Extension(Plugin, MenuRequiredMixin):
    "Shows a menu with shortcuts"

    active_workspace = ""

    async def init(self):
        "initializes the plugin"
        for monitor in await self.hyprctlJSON("monitors"):
            assert isinstance(monitor, dict)
            if monitor["focused"]:
                self.active_workspace = cast(str, monitor["activeWorkspace"]["name"])

    # Commands

    async def run_fetch_client_menu(self):
        "Select a client window and move it to the active workspace"
        await self._ensure_configured()

        clients = await self.hyprctlJSON("clients")

        options = {
            f"{i} | {c['title']}": c
            for i, c in enumerate(clients)
            if c["mapped"] and c["workspace"]["name"] != self.active_workspace
        }

        choice = await self.menu.run(options.keys())

        if choice in options:
            addr = options[choice]["address"]
            await self.hyprctl(
                f"movetoworkspace {self.active_workspace},address:{addr}"
            )

    async def event_workspace(self, wrkspace):
        "track the active workspace"
        self.active_workspace = wrkspace

    async def event_focusedmon(self, mon):
        "track the active workspace"
        _, self.active_workspace = mon.rsplit(",", 1)
