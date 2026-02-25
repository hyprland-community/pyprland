"""Docstring and command name parsing utilities."""

from __future__ import annotations

import re

from .models import CommandArg

__all__ = ["normalize_command_name", "parse_docstring"]

# Regex pattern to match args: <required> or [optional]
_ARG_PATTERN = re.compile(r"([<\[])([^>\]]+)([>\]])")


def normalize_command_name(cmd: str) -> str:
    """Normalize a user-typed command to internal format.

    Converts spaces and hyphens to underscores.
    E.g., "wall rm" -> "wall_rm", "toggle-special" -> "toggle_special"

    Args:
        cmd: User-typed command string

    Returns:
        Normalized command name with underscores
    """
    return cmd.replace("-", "_").replace(" ", "_")


def parse_docstring(docstring: str) -> tuple[list[CommandArg], str, str]:
    """Parse a docstring to extract arguments and descriptions.

    The first line may contain arguments like:
    "<arg> Short description" or "[optional_arg] Short description"

    Args:
        docstring: The raw docstring to parse

    Returns:
        Tuple of (args, short_description, full_description)
        - args: List of CommandArg objects
        - short_description: Text after arguments on first line
        - full_description: Complete docstring
    """
    if not docstring:
        return [], "No description available.", ""

    full_description = docstring.strip()
    lines = full_description.split("\n")
    first_line = lines[0].strip()

    args: list[CommandArg] = []
    last_end = 0

    # Find all args at the start of the line
    for match in _ARG_PATTERN.finditer(first_line):
        # Check if this match is at the expected position (start or after whitespace)
        if match.start() != last_end and first_line[last_end : match.start()].strip():
            # There's non-whitespace before this match, stop parsing args
            break

        bracket_open = match.group(1)
        content = match.group(2)
        required = bracket_open == "<"
        args.append(CommandArg(value=content, required=required))
        last_end = match.end()

        # Skip any whitespace after the arg
        while last_end < len(first_line) and first_line[last_end] == " ":
            last_end += 1

    # The short description is what comes after the args
    if args:
        short_description = first_line[last_end:].strip()
        if not short_description:
            short_description = first_line
    else:
        short_description = first_line

    return args, short_description, full_description
