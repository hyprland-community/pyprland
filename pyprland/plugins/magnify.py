" Toggles workspace zooming "
from .interface import Plugin
import asyncio


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    zoomed = False

    cur_factor = 1

    def ease_out_quad(self, step, start, end, duration):
        """Easing function for animations."""
        step /= duration
        return -end * step * (step - 2) + start

    def animated_eased_zoom(self, start, end, duration):
        """Helper function to animate zoom"""
        for i in range(duration):
            yield self.ease_out_quad(i, start, end - start, duration)

    async def run_zoom(self, *args):
        """[factor] zooms to "factor" or toggles zoom level if factor is ommited"""
        animated = self.config.get("animated", True)
        prev_factor = self.cur_factor
        if args:  # set or update the factor
            relative = args[0][0] in "+-"
            value = int(args[0])

            # compute the factor
            if relative:
                self.cur_factor += value
            else:
                self.cur_factor = value

            # sanity check
            self.cur_factor = max(self.cur_factor, 1)
        else:
            if self.zoomed:
                self.cur_factor = 1
            else:
                self.cur_factor = int(self.config.get("factor", 2))

        if animated:
            start = prev_factor * 10
            end = self.cur_factor * 10
            for i in self.animated_eased_zoom(
                start, end, self.config.get("duration", 15)
            ):
                await self.hyprctl(f"misc:cursor_zoom_factor {i/10}", "keyword")
                await asyncio.sleep(1.0 / 60)
        self.zoomed = self.cur_factor != 1
        await self.hyprctl(f"misc:cursor_zoom_factor {self.cur_factor}", "keyword")
