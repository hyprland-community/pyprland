"""Data models for command handling."""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = ["CLIENT_COMMANDS", "CommandArg", "CommandInfo", "CommandNode"]

# Client-only commands with their docstrings (not sent to daemon)
CLIENT_COMMANDS: dict[str, str] = {
    "edit": """Open the configuration file in $EDITOR, then reload.

Opens pyprland.toml in your preferred editor (EDITOR or VISUAL env var,
defaults to vi). After the editor closes, the configuration is reloaded.""",
    "validate": """Validate the configuration file.

Checks the configuration file for syntax errors and validates plugin
configurations against their schemas. Does not require the daemon.""",
}


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
