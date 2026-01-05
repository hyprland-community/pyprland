"""Template processing for wallpapers plugin."""

import asyncio
import colorsys
import contextlib
import logging
import re
from typing import cast

from ...aioops import aiexists, aiopen
from .imageutils import expand_path
from .models import HEX_LEN, HEX_LEN_HASH


def _set_alpha(color: str, alpha: str) -> str:
    """Set alpha channel for a color."""
    if color.startswith("rgba("):
        return f"{color.rsplit(',', 1)[0]}, {alpha})"
    if len(color) == HEX_LEN:
        r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"
    if len(color) == HEX_LEN_HASH and color.startswith("#"):
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"
    return color


def _set_lightness(hex_color: str, amount: str) -> str:
    """Adjust lightness of a color."""
    # hex_color can be RRGGBB or #RRGGBB
    color = hex_color.lstrip("#")
    if len(color) != HEX_LEN:
        return hex_color

    r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
    h, l_val, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)

    # amount is percentage change, e.g. 20.0 or -10.0
    with contextlib.suppress(ValueError):
        l_val = max(0.0, min(1.0, l_val + (float(amount) / 100.0)))

    nr, ng, nb = colorsys.hls_to_rgb(h, l_val, s)
    new_hex = f"{int(nr * 255):02x}{int(ng * 255):02x}{int(nb * 255):02x}"
    return f"#{new_hex}" if hex_color.startswith("#") else new_hex


async def _apply_filters(content: str, replacements: dict[str, str]) -> str:
    """Apply filters to the content."""
    # Process all template tags {{ ... }}
    # We find all tags first, then replace them.
    # This regex matches {{ variable | filter: arg }} or just {{ variable }}
    # It handles spaces around variable and filter parts.
    tag_pattern = re.compile(r"\{\{\s*([\w\.]+)(?:\s*\|\s*([\w_]+)\s*(?:[:\s])\s*([^}]+))?\s*\}\}")

    def replace_tag(match: re.Match) -> str:
        key = match.group(1)
        filter_name = match.group(2)
        filter_arg = match.group(3)

        value = replacements.get(key)
        if value is None:
            return cast("str", match.group(0))

        if filter_name and filter_arg:
            filter_arg = filter_arg.strip()
            with contextlib.suppress(Exception):
                if filter_name == "set_alpha":
                    return _set_alpha(value, filter_arg)
                if filter_name == "set_lightness":
                    return _set_lightness(value, filter_arg)
            # Fallback if filter fails or unknown
            return str(value)

        return str(value)

    return tag_pattern.sub(replace_tag, content)


class TemplateEngine:
    """Handle template generation."""

    def __init__(self, log: logging.Logger):
        self.log = log

    async def process_single_template(
        self,
        name: str,
        template_config: dict[str, str],
        replacements: dict[str, str],
    ) -> None:
        """Process a single template."""
        if "input_path" not in template_config or "output_path" not in template_config:
            self.log.error("Template %s missing input_path or output_path", name)
            return

        input_path = expand_path(template_config["input_path"])
        output_path = expand_path(template_config["output_path"])

        if not await aiexists(input_path):
            self.log.error("Template input file %s not found", input_path)
            return

        try:
            async with aiopen(input_path, "r") as f:
                content = await f.read()

            content = await _apply_filters(content, replacements)

            async with aiopen(output_path, "w") as f:
                await f.write(content)
            self.log.info("Generated %s from %s", output_path, input_path)

            post_hook = template_config.get("post_hook")
            if post_hook:
                self.log.info("Running post_hook for %s: %s", name, post_hook)
                await asyncio.create_subprocess_shell(post_hook)

        except Exception:  # pylint: disable=broad-exception-caught
            self.log.exception("Error processing template %s", name)
