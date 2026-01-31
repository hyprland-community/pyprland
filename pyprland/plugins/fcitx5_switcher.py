"""A plugin to auto-switch Fcitx5 input method status by window class/title."""

from typing import ClassVar

from ..models import Environment
from ..validation import ConfigField, ConfigItems
from .interface import Plugin


class Extension(Plugin):
    """A plugin to auto-switch Fcitx5 input method status by window class/title."""

    environments: ClassVar[list[Environment]] = [Environment.HYPRLAND]

    config_schema = ConfigItems(
        ConfigField("active_classes", list, default=[], description="Window classes that should activate Fcitx5", category="activation"),
        ConfigField("active_titles", list, default=[], description="Window titles that should activate Fcitx5", category="activation"),
        ConfigField(
            "inactive_classes", list, default=[], description="Window classes that should deactivate Fcitx5", category="deactivation"
        ),
        ConfigField(
            "inactive_titles", list, default=[], description="Window titles that should deactivate Fcitx5", category="deactivation"
        ),
    )

    async def event_activewindowv2(self, _addr: str) -> None:
        """A plugin to auto-switch Fcitx5 input method status by window class/title.

        Args:
            _addr: The address of the active window
        """
        _addr = "0x" + _addr

        active_classes = self.get_config_list("active_classes")
        active_titles = self.get_config_list("active_titles")
        inactive_classes = self.get_config_list("inactive_classes")
        inactive_titles = self.get_config_list("inactive_titles")

        clients = await self.get_clients()
        for client in clients:
            if client["address"] == _addr:
                if client["class_"] in active_classes or client["title"] in active_titles:
                    await self.backend.execute(["execr fcitx5-remote -o"])
                if client["class_"] in inactive_classes or client["title"] in inactive_titles:
                    await self.backend.execute(["execr fcitx5-remote -c"])
