"""Help and documentation functions for pyprland commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .command_registry import build_command_tree, get_all_commands

if TYPE_CHECKING:
    from .manager import Pyprland

__all__ = ["get_command_help", "get_commands_help", "get_help"]


def get_commands_help(manager: Pyprland) -> dict[str, str]:
    """Get the available commands and their short documentation.

    Uses command tree to show parent commands with their subcommands.
    Example: "wall <next|pause|clear|rm|cleanup> (wallpapers)"

    Args:
        manager: The Pyprland manager instance

    Returns:
        Dict mapping command name to short description with source suffix
    """
    all_commands = get_all_commands(manager)
    command_tree = build_command_tree(all_commands)

    result: dict[str, str] = {}

    for root_name, node in sorted(command_tree.items()):
        if node.children:
            # Command with subcommands - show inline
            subcmds = "|".join(sorted(node.children.keys()))
            # Get source from first child with info, or from parent
            source = ""
            for child in node.children.values():
                if child.info:
                    source = child.info.source
                    break
            if not source and node.info:
                source = node.info.source
            desc = node.info.short_description if node.info else ""
            result[root_name] = f"<{subcmds}> {desc} ({source})".strip()
        elif node.info:
            # Regular command
            result[root_name] = f"{node.info.short_description} ({node.info.source})"

    return result


def get_help(manager: Pyprland) -> str:
    """Get the help documentation for all commands.

    Args:
        manager: The Pyprland manager instance
    """
    intro = """Syntax: pypr [command]

If the command is omitted, runs the daemon which will start every configured plugin.

Available commands:
"""
    return intro + "\n".join(f" {name:20s} {doc}" for name, doc in get_commands_help(manager).items())


def get_command_help(manager: Pyprland, command: str) -> str:
    """Get detailed help for a specific command.

    Supports space-separated subcommands: "wall next" -> looks up "wall_next"
    For parent commands with subcommands, shows list of subcommands.

    Args:
        manager: The Pyprland manager instance
        command: Command name to get help for (may contain spaces for subcommands)

    Returns:
        Full docstring with source indicator, or error message if not found
    """
    # Handle space-separated subcommands: "wall next" -> "wall_next"
    command = command.replace("-", "_").replace(" ", "_")
    all_commands = get_all_commands(manager)
    command_tree = build_command_tree(all_commands)

    # Try direct lookup first (e.g., "wall_next" or "toggle")
    if command in all_commands:
        cmd = all_commands[command]
        doc = cmd.full_description
        doc_formatted = doc if doc.endswith("\n") else f"{doc}\n"
        return f"{command.replace('_', ' ')} ({cmd.source})\n\n{doc_formatted}"

    # Check if this is a parent command with subcommands
    if command in command_tree:
        node = command_tree[command]
        if node.children:
            # Show subcommands
            lines = [f"{command} ({node.info.source if node.info else 'unknown'})", ""]

            if node.info and node.info.full_description:
                lines.append(node.info.full_description)
                lines.append("")

            lines.append("Subcommands:")
            for subcmd_name, subcmd_node in sorted(node.children.items()):
                if subcmd_node.info:
                    lines.append(f"  {subcmd_name:15s} {subcmd_node.info.short_description}")
                else:
                    lines.append(f"  {subcmd_name}")
            lines.append("")
            return "\n".join(lines)

    return f"Unknown command: {command}\nRun 'pypr help' for available commands.\n"
