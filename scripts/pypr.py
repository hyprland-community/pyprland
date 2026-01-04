"""Fake pypr CLI to generate auto-completion scripts."""

import argparse
import os
import pathlib

import shtab

TOML_FILE = {
    "bash": "_shtab_greeter_compgen_TOMLFiles",
    "zsh": "_files -g '(*.toml|*.TOML)'",
    "tcsh": "f:*.toml",
}

PREAMBLE = {
    "bash": """
# $1=COMP_WORDS[1]
_shtab_greeter_compgen_TOMLFiles() {
  compgen -d -- $1  # recurse into subdirs
  compgen -f -X '!*?.toml' -- $1
  compgen -f -X '!*?.TOML' -- $1
}
""",
    "zsh": "",
    "tcsh": "",
}


def get_parser():
    """Parses the command line arguments."""
    parser = argparse.ArgumentParser(prog="pypr", description="Pyprland CLI", add_help=False, allow_abbrev=False)
    parser.add_argument(
        "--debug",
        help="Enable debug mode and log to a file",
        metavar="filename",
    ).complete = shtab.FILE
    parser.add_argument(
        "--config",
        help="Use a different configuration file",
        metavar="filename",
        type=pathlib.Path,
    ).complete = TOML_FILE
    shtab.add_argument_to(parser, preamble=PREAMBLE)

    # Base commands
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("dumpjson", help="Dump the current state in JSON format")
    subparsers.add_parser("edit", help="Edit the configuration file")
    subparsers.add_parser("exit", help="Exit the currently running daemon")
    subparsers.add_parser("help", help="Prints this help message")
    subparsers.add_parser("version", help="Prints the current version")
    subparsers.add_parser("reload", help="Reload the configuration file")

    # Scratchpads
    subparsers.add_parser("attach", help="Attach the focused window to the last focused scratchpad")
    show = subparsers.add_parser("show", help="Show the given scratchpad")
    show.add_argument("Scratchpad", help="scratchpad name", nargs="?")
    hide = subparsers.add_parser("hide", help="Hide the given scratchpad")
    hide.add_argument("Scratchpad", help="scratchpad name", nargs="?")
    toggle = subparsers.add_parser("toggle", help="Toggle the given scratchpad")
    toggle.add_argument("Scratchpad", help="scratchpad name", nargs="?")
    # bar
    bar = subparsers.add_parser("bar", help="Starts gBar on the first available monitor")
    bar.add_argument(
        "command",
        help="Starts gBar on the first available monitor",
        nargs="?",
        choices=["restart", "stop"],
    )
    # shortcuts_menu
    menu = subparsers.add_parser("menu", help="Shows the menu")
    menu.add_argument("name", help="submenu to show", nargs="?")
    # toggle_special
    toggle_special = subparsers.add_parser(
        "toggle_special",
        help="Toggle switching the focused window to the special workspace",
    )
    toggle_special.add_argument("name", help="special workspace name", nargs="?")
    # layout_center
    layout_center = subparsers.add_parser("layout_center", help="Change the active window")
    layout_center.add_argument("command", help="Change the active window", choices=["toggle", "next", "prev", "next2", "prev2"])
    # lost_windows
    subparsers.add_parser("attract_lost", help="Brings lost floating windows to the current workspace")
    # shift_monitors
    shift_monitors = subparsers.add_parser("shift_monitors", help="Swaps monitors' workspaces in the given direction")
    shift_monitors.add_argument("direction", help="Swaps monitors' workspaces in the given direction", choices=["+1", "-1"])
    # toggle_dpms
    subparsers.add_parser("toggle_dpms", help="Toggles dpms on/off for every monitor")
    # magnify
    zoom = subparsers.add_parser("zoom", help="Zoom to the given factor")
    zoom.add_argument("factor", help="Zoom to the given factor", nargs="?", choices=["+1", "-1", "++0.5", "--0.5", "1"])
    # Expose
    subparsers.add_parser("expose", help="Expose every client on the active workspace")
    # workspaces_follow_focus
    change_workspace = subparsers.add_parser("change_workspace", help="Switch workspaces of current monitor")
    change_workspace.add_argument("direction", help="direction to switch workspaces", choices=["-1", "+1"], nargs="?")
    # wallpapers
    wall = subparsers.add_parser("wall", help="Skip the current background image")
    wall.add_argument("action", help="Skip the current background image", choices=["next", "clear", "pause", "color"])
    wall.add_argument("param", help="Optional parameter (e.g. color hex)", nargs="?")
    # fetch_client_menu
    subparsers.add_parser(
        "fetch_client_menu",
        help="Select a client window and move it to the active workspace",
    )
    subparsers.add_parser("unfetch_client", help="Returns a window back to its origin")
    # monitors
    subparsers.add_parser("relayout", help="Recompute & apply every monitors's layout")

    return parser


if "RUN" in os.environ:
    get_parser().parse_args()
