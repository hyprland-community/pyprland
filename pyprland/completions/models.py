"""Data models and constants for shell completions.

Contains the data structures used to represent command completions
and configuration constants for completion generation.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..plugins.wallpapers.models import ColorScheme

__all__ = [
    "DEFAULT_PATHS",
    "HINT_ARGS",
    "KNOWN_COMPLETIONS",
    "SCRATCHPAD_COMMANDS",
    "CommandCompletion",
    "CompletionArg",
]

# Default user-level completion paths
DEFAULT_PATHS = {
    "bash": "~/.local/share/bash-completion/completions/pypr",
    "zsh": "~/.zsh/completions/_pypr",
    "fish": "~/.config/fish/completions/pypr.fish",
}

# Commands that use scratchpad names for completion
SCRATCHPAD_COMMANDS = {"toggle", "show", "hide", "attach"}

# Known static completions for specific arg names
KNOWN_COMPLETIONS: dict[str, list[str]] = {
    "scheme": [c.value for c in ColorScheme if c.value] + ["fluorescent"],  # Include alias
    "direction": ["1", "-1"],
}

# Args that should show as hints (no actual completion values)
HINT_ARGS: dict[str, str] = {
    "#RRGGBB": "#RRGGBB (hex color)",
    "color": "#RRGGBB (hex color)",
    "factor": "number (zoom level)",
}


@dataclass
class CompletionArg:
    """Argument completion specification."""

    position: int  # 1-based position after command
    completion_type: str  # "choices", "literal", "hint", "file", "none"
    values: list[str] = field(default_factory=list)  # Values to complete or hint text
    required: bool = True  # Whether the arg is required
    description: str = ""  # Description for zsh


@dataclass
class CommandCompletion:
    """Full completion spec for a command."""

    name: str
    args: list[CompletionArg] = field(default_factory=list)
    description: str = ""
    subcommands: dict[str, CommandCompletion] = field(default_factory=dict)  # For hierarchical commands
