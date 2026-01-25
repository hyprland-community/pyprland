"""General utility functions."""

import asyncio
import contextlib
import re
from typing import Any

from .models import MonitorInfo

__all__ = [
    "apply_filter",
    "apply_variables",
    "is_rotated",
    "merge",
    "notify_send",
]


def merge(merged: dict[str, Any], obj2: dict[str, Any], replace: bool = False) -> dict[str, Any]:
    """Merge the content of d2 into d1.

    Args:
        merged (dict): Dictionary to merge into
        obj2 (dict): Dictionary to merge from
        replace (bool): If True, replace content of lists and dicts recursively, deleting missing keys in src.

    Returns:
         dictionary with the merged content

    Eg:
        merge({"a": {"b": 1}}, {"a": {"c": 2}}) == {"a": {"b": 1, "c": 2}}

    """
    if replace:
        to_remove = [k for k in merged if k not in obj2]
        for k in to_remove:
            del merged[k]

    for key, value in obj2.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            # If both values are dictionaries, recursively merge them
            merge(merged[key], value, replace=replace)
        elif key in merged and isinstance(merged[key], list) and isinstance(value, list):
            # If both values are lists, concatenate them
            if replace:
                merged[key].clear()
                merged[key].extend(value)
            else:
                merged[key] += value
        else:
            # Otherwise, update the value or add the key-value pair
            merged[key] = value
    return merged


def apply_variables(template: str, variables: dict[str, str]) -> str:
    """Replace [var_name] with content from supplied variables.

    Args:
        template: the string template
        variables: a dict containing the variables to replace

    Returns:
        The template with variables replaced
    """
    pattern = r"\[([^\[\]]+)\]"

    def replace(match: re.Match[str]) -> str:
        var_name = match.group(1)
        return variables.get(var_name, match.group(0))

    return re.sub(pattern, replace, template)


def apply_filter(text: str, filt_cmd: str) -> str:
    """Apply filters to text.

    Currently supports only "s" command fom vim/ed

    Args:
        text: The text to filter
        filt_cmd: The filter command (e.g. "s/foo/bar/g")

    Returns:
        The filtered text
    """
    if not filt_cmd:
        return text
    if filt_cmd[0] == "s":  # vi-like substitute
        try:
            sep = filt_cmd[1]
            parts = filt_cmd.split(sep)
            min_substitute_parts = 3  # s/base/replacement/ requires at least 3 parts
            if len(parts) < min_substitute_parts:
                return text
            (_, base, replacement, opts) = parts[:4]
            return re.sub(base, replacement, text, count=0 if "g" in opts else 1)
        except (IndexError, ValueError):
            return text
    return text


def is_rotated(monitor: MonitorInfo) -> bool:
    """Return True if the monitor is rotated.

    Args:
        monitor: The monitor info dictionary

    Returns:
        True if the monitor is rotated (transform is 1, 3, 5, or 7)
    """
    return monitor["transform"] in {1, 3, 5, 7}


async def notify_send(text: str, duration: int = 3000, color: str | None = None, icon: str | None = None) -> None:
    """Send a notification using notify-send.

    Args:
        text: The text to display
        duration: The duration in milliseconds
        color: The color to use (currently unused by notify-send but kept for API compatibility)
        icon: The icon to use
    """
    del color  # unused
    args = ["notify-send", text, f"--expire-time={duration}", "--app-name=pyprland"]
    if icon:
        args.append(f"--icon={icon}")

    # notify-send doesn't support color directly in standard implementations without custom patches or specific notification daemons
    # so we ignore color for now to keep it generic, or we could use hints if we knew the daemon supported them.

    with contextlib.suppress(FileNotFoundError):
        # We don't care about the output
        await asyncio.create_subprocess_exec(*args)
