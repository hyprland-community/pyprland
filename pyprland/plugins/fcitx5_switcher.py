"""A plugin to auto-switch Fcitx5 input method status by window class/title."""

from .interface import Plugin


class Extension(Plugin):
    """A plugin to auto-switch Fcitx5 input method status by window class/title."""

    async def event_activewindowv2(self, _addr: str) -> None:
        """A plugin to auto-switch Fcitx5 input method status by window class/title.

        Args:
            _addr: The address of the active window
        """
        _addr = "0x" + _addr

        active_classes = self.config.get("active_classes", [])
        active_titles = self.config.get("active_titles", [])
        inactive_classes = self.config.get("inactive_classes", [])
        inactive_titles = self.config.get("inactive_titles", [])

        clients = await self.get_clients()
        for client in clients:
            if client["address"] == _addr:
                if client["class_"] in active_classes or client["title"] in active_titles:
                    await self.hyprctl(["execr fcitx5-remote -o"])
                if client["class_"] in inactive_classes or client["title"] in inactive_titles:
                    await self.hyprctl(["execr fcitx5-remote -c"])
