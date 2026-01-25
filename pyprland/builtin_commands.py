"""Built-in command definitions for pyprland.

This module is separate to avoid circular imports between help.py and completions.py.
"""

from pyprland.constants import SUPPORTED_SHELLS

# Built-in commands: (short_description, detail, subcommands)
# - short: Used in `pypr help` command list
# - detail: Appended for `pypr help <command>`
# - subcommands: For shell completion
BUILTIN_COMMANDS: dict[str, tuple[str, str, list[str]]] = {
    "help": (
        "Show available commands or detailed help for a specific command.",
        "Usage:\n  pypr help           List all commands\n  pypr help <command> Show detailed help",
        [],
    ),
    "exit": ("Terminate the pyprland daemon.", "", []),
    "version": ("Show the pyprland version.", "", []),
    "reload": (
        "Reload the configuration file.",
        "New plugins will be loaded and configuration options will be updated.\n"
        "Most plugins will use the new values on the next command invocation.",
        [],
    ),
    "dumpjson": ("Dump the configuration in JSON format (after includes are processed).", "", []),
    "edit": ("Edit the configuration file using $EDITOR (or vi), then reload.", "Not available in pypr-client.", []),
    "validate": (
        "Validate the configuration file against plugin schemas.",
        "Checks all plugin configurations for errors and warnings.\n"
        "Works without the daemon running.\n\nNote: Not available in pypr-client.",
        [],
    ),
    "compgen": (
        f"Generate shell completions. <{'|'.join(SUPPORTED_SHELLS)}> [path]",
        "Usage:\n  pypr compgen <shell>        Install to default user path\n"
        "  pypr compgen <shell> <path> Install to custom path\n\n"
        "Completions include scratchpad names for toggle/show/hide commands.",
        list(SUPPORTED_SHELLS),
    ),
}
