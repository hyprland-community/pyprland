"""CLI handlers for shell completion commands.

Provides the handle_compgen function used by the pyprland plugin
to generate and install shell completions.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..constants import SUPPORTED_SHELLS
from .discovery import get_command_completions
from .generators import GENERATORS
from .models import DEFAULT_PATHS

if TYPE_CHECKING:
    from ..manager import Pyprland

__all__ = ["get_default_path", "handle_compgen"]


def get_default_path(shell: str) -> str:
    """Get the default user-level completion path for a shell.

    Args:
        shell: Shell type ("bash", "zsh", or "fish")

    Returns:
        Expanded absolute path to the default completion file
    """
    return str(Path(DEFAULT_PATHS[shell]).expanduser())


def _get_success_message(shell: str, output_path: str, used_default: bool) -> str:
    """Generate a friendly success message after installing completions.

    Args:
        shell: Shell type
        output_path: Path where completions were written
        used_default: Whether the default path was used

    Returns:
        User-friendly success message
    """
    # Use ~ in display path for readability
    display_path = output_path.replace(str(Path.home()), "~")

    if not used_default:
        return f"Completions written to {display_path}"

    if shell == "bash":
        return f"Completions installed to {display_path}\nReload your shell or run: source ~/.bashrc"

    if shell == "zsh":
        return (
            f"Completions installed to {display_path}\n"
            "Ensure ~/.zsh/completions is in your fpath. Add to ~/.zshrc:\n"
            "  fpath=(~/.zsh/completions $fpath)\n"
            "  autoload -Uz compinit && compinit\n"
            "Then reload your shell."
        )

    if shell == "fish":
        return f"Completions installed to {display_path}\nReload your shell or run: source ~/.config/fish/config.fish"

    return f"Completions written to {display_path}"


def _parse_compgen_args(args: str) -> tuple[bool, str, str | None]:
    """Parse and validate compgen command arguments.

    Args:
        args: Arguments after "compgen" (e.g., "zsh" or "zsh default")

    Returns:
        Tuple of (success, shell_or_error, path_arg):
        - On success: (True, shell, path_arg or None)
        - On failure: (False, error_message, None)
    """
    parts = args.split(None, 1)
    if not parts:
        shells = "|".join(SUPPORTED_SHELLS)
        return (False, f"Usage: compgen <{shells}> [default|path]", None)

    shell = parts[0]
    if shell not in SUPPORTED_SHELLS:
        return (False, f"Unsupported shell: {shell}. Supported: {', '.join(SUPPORTED_SHELLS)}", None)

    path_arg = parts[1] if len(parts) > 1 else None
    if path_arg is not None and path_arg != "default" and not path_arg.startswith(("/", "~")):
        return (False, "Relative paths not supported. Use absolute path, ~/path, or 'default'.", None)

    return (True, shell, path_arg)


def handle_compgen(manager: Pyprland, args: str) -> tuple[bool, str]:
    """Handle compgen command with path semantics.

    Args:
        manager: The Pyprland manager instance
        args: Arguments after "compgen" (e.g., "zsh" or "zsh default")

    Returns:
        Tuple of (success, result):
        - No path arg: result is the script content
        - With path arg: result is success/error message
    """
    success, shell_or_error, path_arg = _parse_compgen_args(args)
    if not success:
        return (False, shell_or_error)

    shell = shell_or_error

    try:
        commands = get_command_completions(manager)
        content = GENERATORS[shell](commands)
    except (KeyError, ValueError, TypeError) as e:
        return (False, f"Failed to generate completions: {e}")

    if path_arg is None:
        return (True, content)

    # Determine output path
    if path_arg == "default":
        output_path = get_default_path(shell)
        used_default = True
    else:
        output_path = str(Path(path_arg).expanduser())
        used_default = False

    manager.log.debug("Writing completions to: %s", output_path)

    # Write to file
    try:
        parent_dir = Path(output_path).parent
        parent_dir.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(content, encoding="utf-8")
    except OSError as e:
        return (False, f"Failed to write completion file: {e}")

    return (True, _get_success_message(shell, output_path, used_default))
