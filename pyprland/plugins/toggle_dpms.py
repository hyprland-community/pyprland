"""Toggle monitors on or off."""

from ..models import Environment
from .interface import Plugin


class Extension(Plugin, environments=[Environment.HYPRLAND]):
    """Toggles the DPMS status of every plugged monitor."""

    async def run_toggle_dpms(self) -> None:
        """Toggle dpms on/off for every monitor."""
        monitors = await self.backend.get_monitors()
        powered_off = any(m["dpmsStatus"] for m in monitors)
        if not powered_off:
            await self.backend.execute("dpms on")
        else:
            await self.backend.execute("dpms off")
