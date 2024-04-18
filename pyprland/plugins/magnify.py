" Toggles workspace zooming "
from .interface import Plugin
import asyncio


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    zoomed = False

    cur_factor = 1

    async def run_zoom(self, *args):
        """[factor] zooms to "factor" or toggles zoom level if factor is ommited"""
        animated = self.config.get("animated", True)
        if args:  # set or update the factor
            relative = args[0][0] in "+-"
            value = int(args[0])
            prev_factor = self.cur_factor

            # compute the factor
            if relative:
                self.cur_factor += value
            else:
                self.cur_factor = value

            # sanity check
            self.cur_factor = max(self.cur_factor, 1)

            # apply the factor
            if animated:
                if prev_factor < self.cur_factor:
                    for n in range(prev_factor * 10, self.cur_factor * 10):
                        await self.hyprctl(
                            f"misc:cursor_zoom_factor {n/10.0}", "keyword"
                        )
                        await asyncio.sleep(1.0 / 60)
                else:
                    for n in reversed(range(self.cur_factor * 10, prev_factor * 10)):
                        await self.hyprctl(
                            f"misc:cursor_zoom_factor {n/10.0}", "keyword"
                        )
                        await asyncio.sleep(1.0 / 60)
        else:  # toggle
            if self.zoomed:
                if animated:
                    for n in reversed(range(10, self.cur_factor * 10)):
                        await self.hyprctl(
                            f"misc:cursor_zoom_factor {n/10.0}", "keyword"
                        )
                        await asyncio.sleep(1.0 / 60)
                self.cur_factor = 1
            else:
                new_factor = int(self.config.get("factor", 2))
                if animated:
                    for n in range(self.cur_factor * 10, new_factor * 10):
                        await self.hyprctl(
                            f"misc:cursor_zoom_factor {n/10.0}", "keyword"
                        )
                        await asyncio.sleep(1.0 / 60)
                self.cur_factor = int(self.config.get("factor", 2))
        self.zoomed = self.cur_factor != 1
        await self.hyprctl(f"misc:cursor_zoom_factor {self.cur_factor}", "keyword")
