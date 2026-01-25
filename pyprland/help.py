"""Help and documentation functions for pyprland commands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pyprland.builtin_commands import BUILTIN_COMMANDS

if TYPE_CHECKING:
    from pyprland.manager import Pyprland

__all__ = ["BUILTIN_COMMANDS", "get_commands_help", "get_help", "get_command_help"]


def get_commands_help(manager: Pyprland) -> dict[str, str]:
    """Get the available commands and their short documentation.

    Args:
        manager: The Pyprland manager instance

    Returns:
        Dict mapping command name to short description
    """
    # Start with built-in commands (use short description)
    docs = {cmd: info[0] for cmd, info in BUILTIN_COMMANDS.items()}

    # Add plugin commands
    for plug in manager.plugins.values():
        for name in dir(plug):
            if not name.startswith("run_"):
                continue
            fn = getattr(plug, name)
            if callable(fn):
                doc_txt = fn.__doc__ or "N/A"
                first_line = doc_txt.split("\n", 1)[0]  # Use first line only
                docs[name[4:]] = f"{first_line} [{plug.name}]"
    return docs


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

    Args:
        manager: The Pyprland manager instance
        command: Command name to get help for

    Returns:
        Full docstring with plugin name, or error message if not found
    """
    # Normalize command name (support dashes)
    command = command.replace("-", "_")

    # Check built-in commands first
    if command in BUILTIN_COMMANDS:
        short, detail, _ = BUILTIN_COMMANDS[command]
        full_doc = f"{short}\n\n{detail}" if detail else short
        return f"{command}\n\n{full_doc}\n"

    # Search plugins for run_{command}
    for plugin in manager.plugins.values():
        method = getattr(plugin, f"run_{command}", None)
        if method and callable(method):
            doc = method.__doc__ or "No documentation available."
            return f"{command} [{plugin.name}]\n\n{doc}" if doc.endswith("\n") else f"{command} [{plugin.name}]\n\n{doc}\n"

    return f"Unknown command: {command}\nRun 'pypr help' for available commands.\n"
