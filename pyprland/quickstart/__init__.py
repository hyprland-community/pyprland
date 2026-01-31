"""Pyprland quickstart configuration wizard - standalone script."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Args:
    """Parsed command line arguments."""

    plugins: list[str] | None = None
    dry_run: bool = False
    output: Path | None = None


def parse_args(argv: list[str]) -> Args:
    """Parse command line arguments.

    Args:
        argv: Command line arguments (without program name)

    Returns:
        Parsed arguments
    """
    args = Args()
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--plugins" and i + 1 < len(argv):
            args.plugins = [p.strip() for p in argv[i + 1].split(",")]
            i += 2
        elif arg == "--dry-run":
            args.dry_run = True
            i += 1
        elif arg == "--output" and i + 1 < len(argv):
            args.output = Path(argv[i + 1])
            i += 2
        else:
            i += 1
    return args


def print_help() -> None:
    """Print minimal help message."""
    print("Usage: pypr-quickstart [OPTIONS]")
    print()
    print("Interactive configuration wizard for Pyprland.")
    print()
    print("Options:")
    print("  --plugins PLUGINS   Comma-separated plugins to configure (skip selection)")
    print("  --dry-run           Preview config without writing")
    print("  --output PATH       Custom output path")
    print("  --help              Show this message")


def main() -> None:
    """Entry point for pypr-quickstart command."""
    # Handle --help early
    if "--help" in sys.argv or "-h" in sys.argv:
        print_help()
        sys.exit(0)

    # Check questionary dependency
    try:
        import questionary  # noqa: F401, PLC0415  # pylint: disable=unused-import,import-outside-toplevel
    except ImportError:
        print("Error: The quickstart wizard requires additional dependencies.")
        print("Install with: pip install 'pyprland[quickstart]'")
        sys.exit(1)

    from .wizard import run_wizard  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

    # Parse CLI args
    args = parse_args(sys.argv[1:])

    try:
        run_wizard(
            plugins=args.plugins,
            dry_run=args.dry_run,
            output=args.output,
        )
    except KeyboardInterrupt:
        print("\n\nWizard cancelled.")
        sys.exit(1)


if __name__ == "__main__":
    main()
