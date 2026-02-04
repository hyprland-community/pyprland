"""Hierarchical command tree building and display name utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .models import CommandInfo, CommandNode
from .parsing import normalize_command_name

if TYPE_CHECKING:
    from collections.abc import Iterable

__all__ = ["build_command_tree", "get_display_name", "get_parent_prefixes"]


def get_parent_prefixes(commands: dict[str, str] | Iterable[str]) -> set[str]:
    """Identify prefixes that have multiple child commands from the same source.

    A prefix becomes a parent node when more than one command from the
    SAME source/plugin shares it. This prevents unrelated commands like
    toggle_special and toggle_dpms (from different plugins) from being grouped.

    Args:
        commands: Either a dict mapping command name -> source/plugin name,
                  or an iterable of command names (legacy, no source filtering)

    Returns:
        Set of prefixes that should become parent nodes
    """
    # Handle legacy call with just command names (no source info)
    if not isinstance(commands, dict):
        commands = dict.fromkeys(commands, "")

    # Group commands by (prefix, source) to find true hierarchies
    prefix_source_counts: dict[tuple[str, str], int] = {}
    for name, source in commands.items():
        parts = name.split("_")
        for i in range(1, len(parts)):
            prefix = "_".join(parts[:i])
            key = (prefix, source)
            prefix_source_counts[key] = prefix_source_counts.get(key, 0) + 1

    # A prefix is a parent only if multiple commands from same source share it
    return {prefix for (prefix, _source), count in prefix_source_counts.items() if count > 1}


def get_display_name(cmd_name: str, parent_prefixes: set[str]) -> str:
    """Get the user-facing display name for a command.

    Converts underscore-separated hierarchical commands to space-separated.
    E.g., "wall_rm" -> "wall rm" if "wall" is a parent prefix.
    Non-hierarchical commands stay unchanged: "shift_monitors" -> "shift_monitors"

    Args:
        cmd_name: The internal command name (underscore-separated)
        parent_prefixes: Set of prefixes that have multiple children

    Returns:
        The display name (space-separated for hierarchical commands)
    """
    parts = cmd_name.split("_")
    for i in range(1, len(parts)):
        prefix = "_".join(parts[:i])
        if prefix in parent_prefixes:
            subcommand = "_".join(parts[i:])
            return f"{prefix} {subcommand}"
    return cmd_name


def build_command_tree(commands: dict[str, CommandInfo]) -> dict[str, CommandNode]:
    """Build hierarchical command tree from flat command names.

    Groups commands with shared prefixes into a tree structure.
    For example, wall_next, wall_pause, wall_clear become children of "wall".

    Only creates hierarchy when multiple commands share a prefix:
    - wall_next + wall_pause -> wall: {next, pause}
    - layout_center (alone) -> layout_center (no split)

    Accepts command names in both formats:
    - Internal format: wall_next (underscore-separated)
    - Display format: wall next (space-separated)

    Args:
        commands: Dict mapping command name to CommandInfo

    Returns:
        Dict mapping root command names to CommandNode trees
    """
    # Normalize names to internal format (underscore) for tree building
    normalized_commands = {normalize_command_name(name): info for name, info in commands.items()}
    parent_prefixes = get_parent_prefixes(normalized_commands.keys())

    # Build the tree
    roots: dict[str, CommandNode] = {}

    for name, info in sorted(normalized_commands.items()):
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
                root_info = normalized_commands.get(root_name)
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
