" Toggles workspace zooming "
from .interface import Plugin


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    zoomed = False

    cur_factor = 1

    async def run_zoom(self, *args):
        """[factor] zooms to "factor" or toggles zoom level if factor is ommited"""
        if args:  # set or update the factor
            relative = args[0][0] in "+-"
            value = int(args[0])

            # compute the factor
            if relative:
                self.cur_factor += value
            else:
                self.cur_factor = value

            # sanity check
            if self.cur_factor <= 1.0:
                self.cur_factor = 1

            # apply the factor
            self.zoomed = self.cur_factor != 1
            await self.hyprctl(f"misc:cursor_zoom_factor {self.cur_factor}", "keyword")
        else:  # toggle
            if self.zoomed:
                self.cur_factor = 1
                await self.hyprctl("misc:cursor_zoom_factor 1", "keyword")
            else:
                self.cur_factor = int(self.config.get("factor", 2))
                await self.hyprctl(
                    f"misc:cursor_zoom_factor {self.cur_factor}", "keyword"
                )
            self.zoomed = not self.zoomed
