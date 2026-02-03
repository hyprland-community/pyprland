"""Shell completion generators.

Provides generator functions for each supported shell.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .bash import generate_bash
from .fish import generate_fish
from .zsh import generate_zsh

if TYPE_CHECKING:
    from collections.abc import Callable

    from ..models import CommandCompletion

__all__ = ["GENERATORS", "generate_bash", "generate_fish", "generate_zsh"]

GENERATORS: dict[str, Callable[[dict[str, CommandCompletion]], str]] = {
    "bash": generate_bash,
    "zsh": generate_zsh,
    "fish": generate_fish,
}
