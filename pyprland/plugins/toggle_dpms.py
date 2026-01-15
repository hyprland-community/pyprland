"""Toggle monitors on or off."""

from typing import Any, cast  # pylint: disable=unused-import

from .interface import Plugin


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    """Toggle monitors on or off."""

    environments = ["hyprland"]

    async def run_toggle_dpms(self) -> None:
        """Toggle dpms on/off for every monitor."""
        monitors = cast("list[dict[str, Any]]", await self.backend.execute_json("monitors"))
        powered_off = any(m["dpmsStatus"] for m in monitors)
        if not powered_off:
            await self.backend.execute("dpms on")
        else:
            await self.backend.execute("dpms off")
