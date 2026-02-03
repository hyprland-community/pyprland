"""Command registry - unified command discovery and metadata.

Provides a single source of truth for:
- Parsing docstring arguments (<required> / [optional])
- Extracting commands from plugins (instances or classes)
- Including client-only commands

Used by help.py, completions.py, and generate_plugin_docs.py.
"""

from __future__ import annotations

import inspect
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .client import CLIENT_COMMANDS

if TYPE_CHECKING:
    from .manager import Pyprland

__all__ = [
    "CommandArg",
    "CommandInfo",
    "CommandNode",
    "build_command_tree",
    "extract_commands_from_object",
    "get_all_commands",
    "get_client_commands",
    "parse_docstring",
]


@dataclass
class CommandArg:
    """An argument parsed from a command's docstring."""

    value: str  # e.g., "next|pause|clear" or "name"
    required: bool  # True for <arg>, False for [arg]


@dataclass
class CommandInfo:
    """Complete information about a command."""

    name: str
    args: list[CommandArg]
    short_description: str
    full_description: str
    source: str  # "built-in", plugin name, or "client"


@dataclass
class CommandNode:
    """A node in the command hierarchy.

    Used to represent commands with subcommands (e.g., "wall next", "wall pause").
    A node can have both its own handler (info) and children subcommands.
    """

    name: str  # The segment name (e.g., "wall" or "next")
    full_name: str  # Full command name (e.g., "wall" or "wall_next")
    info: CommandInfo | None = None  # Command info if this node is callable
    children: dict[str, CommandNode] = field(default_factory=dict)


# Regex pattern to match args: <required> or [optional]
_ARG_PATTERN = re.compile(r"([<\[])([^>\]]+)([>\]])")


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


def extract_commands_from_object(obj: object, source: str) -> list[CommandInfo]:
    """Extract commands from a plugin class or instance.

    Works with both classes (for docs generation) and instances (runtime).
    Looks for methods starting with "run_" and extracts their docstrings.

    Args:
        obj: A plugin class or instance
        source: The source identifier (plugin name, "built-in", or "client")

    Returns:
        List of CommandInfo objects
    """
    commands: list[CommandInfo] = []

    for name in dir(obj):
        if not name.startswith("run_"):
            continue

        method = getattr(obj, name)
        if not callable(method):
            continue

        command_name = name[4:]  # Remove 'run_' prefix
        docstring = inspect.getdoc(method) or ""

        args, short_desc, full_desc = parse_docstring(docstring)

        commands.append(
            CommandInfo(
                name=command_name,
                args=args,
                short_description=short_desc,
                full_description=full_desc,
                source=source,
            )
        )

    return commands


def get_client_commands() -> list[CommandInfo]:
    """Get client-only commands (edit, validate).

    These commands run on the client side and don't go through the daemon.

    Returns:
        List of CommandInfo for client-only commands
    """
    commands: list[CommandInfo] = []
    for name, doc in CLIENT_COMMANDS.items():
        args, short_desc, full_desc = parse_docstring(doc)
        commands.append(
            CommandInfo(
                name=name,
                args=args,
                short_description=short_desc,
                full_description=full_desc,
                source="client",
            )
        )
    return commands


def get_all_commands(manager: Pyprland) -> dict[str, CommandInfo]:
    """Get all commands from plugins and client.

    Args:
        manager: The Pyprland manager instance with loaded plugins

    Returns:
        Dict mapping command name to CommandInfo
    """
    commands: dict[str, CommandInfo] = {}

    # Extract from all plugins
    for plugin in manager.plugins.values():
        source = "built-in" if plugin.name == "pyprland" else plugin.name
        for cmd in extract_commands_from_object(plugin, source):
            commands[cmd.name] = cmd

    # Add client-only commands
    for cmd in get_client_commands():
        commands[cmd.name] = cmd

    return commands


def build_command_tree(commands: dict[str, CommandInfo]) -> dict[str, CommandNode]:
    """Build hierarchical command tree from flat command names.

    Groups commands with shared prefixes into a tree structure.
    For example, wall_next, wall_pause, wall_clear become children of "wall".

    Only creates hierarchy when multiple commands share a prefix:
    - wall_next + wall_pause -> wall: {next, pause}
    - layout_center (alone) -> layout_center (no split)

    Args:
        commands: Dict mapping command name to CommandInfo

    Returns:
        Dict mapping root command names to CommandNode trees
    """
    # Count how many commands share each prefix
    prefix_counts: dict[str, int] = {}
    for name in commands:
        parts = name.split("_")
        for i in range(1, len(parts)):
            prefix = "_".join(parts[:i])
            prefix_counts[prefix] = prefix_counts.get(prefix, 0) + 1

    # Identify prefixes that should become parent nodes (>1 command shares them)
    parent_prefixes = {prefix for prefix, count in prefix_counts.items() if count > 1}

    # Build the tree
    roots: dict[str, CommandNode] = {}

    for name, info in sorted(commands.items()):
        parts = name.split("_")

        # Find the longest parent prefix for this command
        parent_depth = 0
        for i in range(1, len(parts)):
            prefix = "_".join(parts[:i])
            if prefix in parent_prefixes:
                parent_depth = i

        if parent_depth == 0:
            # No parent prefix - this is a root command
            if name not in roots:
                roots[name] = CommandNode(name=name, full_name=name, info=info)
            else:
                roots[name].info = info
        else:
            # Has a parent prefix - add to tree
            root_name = "_".join(parts[:parent_depth])

            # Ensure root node exists
            if root_name not in roots:
                # Check if root itself is a command
                root_info = commands.get(root_name)
                roots[root_name] = CommandNode(name=root_name, full_name=root_name, info=root_info)

            # Add this command as a child
            if name != root_name:
                child_name = "_".join(parts[parent_depth:])
                roots[root_name].children[child_name] = CommandNode(
                    name=child_name,
                    full_name=name,
                    info=info,
                )

    return roots
