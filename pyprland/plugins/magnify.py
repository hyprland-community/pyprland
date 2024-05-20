"""Toggles workspace zooming."""

import asyncio
from collections.abc import Iterable

from .interface import Plugin


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    """Control workspace zooming."""

    zoomed = False

    cur_factor = 1.0

    def ease_out_quad(self, step: float, start: int, end: int, duration: int) -> float:
        """Easing function for animations."""
        step /= duration
        return -end * step * (step - 2) + start

    def animated_eased_zoom(self, start: int, end: int, duration: int) -> Iterable[float]:
        """Add easing to an animation.

        This function is a generator that yields the next value of the animation

        Args:
            start (float): starting value
            end (float): ending value
            duration (int): duration of the animation
        """
        for i in range(duration):
            yield self.ease_out_quad(i, start, end - start, duration)

    async def run_zoom(self, *args) -> None:
        """[factor] zooms to "factor" or toggles zoom level if factor is omitted.

        If factor is omitted, it toggles between the configured zoom level and no zoom.
        """
        duration = self.config.get("duration", 15)
        animated = bool(duration)
        prev_factor = self.cur_factor
        expo = False
        if args:  # set or update the factor
            relative = args[0][0] in "+-"
            expo = args[0][1] in "+-"
            value = float(args[0][1:]) if expo else float(args[0])

            # compute the factor
            if relative:
                self.cur_factor += value
            else:
                self.cur_factor = value

            # sanity check
            self.cur_factor = max(self.cur_factor, 1)
        elif self.zoomed:
            self.cur_factor = 1
        else:
            self.cur_factor = float(self.config.get("factor", 2.0))

        self.cur_factor = max(self.cur_factor, 1)

        if animated:
            start = (2.0 ** (prev_factor - 1) if expo else prev_factor) * 10
            end = (2.0 ** (self.cur_factor - 1) if expo else self.cur_factor) * 10
            for i in self.animated_eased_zoom(start, end, duration):
                await self.hyprctl(f"misc:cursor_zoom_factor {i / 10}", "keyword")
                await asyncio.sleep(1.0 / 60)
        self.zoomed = self.cur_factor != 1
        factor = 2 ** (self.cur_factor - 1) if expo else self.cur_factor
        await self.hyprctl(f"misc:cursor_zoom_factor {factor}", "keyword")
