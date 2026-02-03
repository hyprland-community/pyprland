"""Shell completion generators for pyprland.

Generates dynamic shell completions based on loaded plugins and configuration.
Supports positional argument awareness with type-specific completions.

This package provides:
- Command completion discovery from loaded plugins
- Shell-specific completion script generators (bash, zsh, fish)
- CLI handler for the `pypr compgen` command
"""

from __future__ import annotations

from .discovery import get_command_completions
from .generators import GENERATORS
from .handlers import get_default_path, handle_compgen
from .models import CommandCompletion, CompletionArg

__all__ = [
    "GENERATORS",
    "CommandCompletion",
    "CompletionArg",
    "get_command_completions",
    "get_default_path",
    "handle_compgen",
]
