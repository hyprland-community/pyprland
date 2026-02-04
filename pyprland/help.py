"""Help and documentation functions for pyprland commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .command_registry import build_command_tree, get_all_commands

if TYPE_CHECKING:
    from .manager import Pyprland

__all__ = ["get_command_help", "get_commands_help", "get_help"]


def get_commands_help(manager: Pyprland) -> dict[str, tuple[str, str]]:
    """Get the available commands and their short documentation.

    Uses command tree to show parent commands with their subcommands.
    Example: "wall" -> ("<next|pause|clear|rm|cleanup>", "wallpapers")

    Args:
        manager: The Pyprland manager instance

    Returns:
        Dict mapping command name to (short_description, source) tuple
    """
    all_commands = get_all_commands(manager)
    command_tree = build_command_tree(all_commands)

    result: dict[str, tuple[str, str]] = {}

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
            result[root_name] = (f"<{subcmds}> {desc}".strip(), source)
        elif node.info:
            # Regular command
            result[root_name] = (node.info.short_description, node.info.source)

    return result


def get_help(manager: Pyprland) -> str:
    """Get the help documentation for all commands.

    Commands are grouped by plugin, with built-in commands listed first.
    Client-only commands (pypr only, not pypr-client) are marked with *.

    Args:
        manager: The Pyprland manager instance
    """
    intro = """Syntax: pypr [command]

If the command is omitted, runs the daemon which will start every configured plugin.

Available commands:
"""
    commands_help = get_commands_help(manager)

    # Group by source (plugin), merging "client" into "built-in"
    by_source: dict[str, list[tuple[str, str, bool]]] = {}
    for name, (desc, source) in commands_help.items():
        # Mark client commands and merge into built-in
        is_pypr_only = source == "client"
        group = "built-in" if source in ("built-in", "client") else source
        by_source.setdefault(group, []).append((name, desc, is_pypr_only))

    # Build output grouped by source, built-in first
    lines: list[str] = []
    sources = sorted(by_source.keys(), key=lambda s: (s != "built-in", s))

    for source in sources:
        # Header with pypr-only note for built-in
        if source == "built-in":
            lines.append(f"\n{source} (* = pypr only):")
        else:
            lines.append(f"\n{source}:")

        # Sort commands: regular first, then pypr-only
        cmds = sorted(by_source[source], key=lambda x: (x[2], x[0]))
        for name, desc, is_pypr_only in cmds:
            prefix = "* " if is_pypr_only else "  "
            lines.append(f"{prefix}{name:20s} {desc}")

    return intro + "\n".join(lines)


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
            # Get source from parent info, or first child with info
            source = node.info.source if node.info else ""
            if not source:
                for child in node.children.values():
                    if child.info:
                        source = child.info.source
                        break
            lines = [f"{command} ({source or 'unknown'})", ""]

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
