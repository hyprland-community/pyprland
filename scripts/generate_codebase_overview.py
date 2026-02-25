#!/usr/bin/env python3
"""Generate CODEBASE_OVERVIEW.md from module docstrings.

Parses all Python files in the pyprland package, extracts module docstrings
and __all__ exports, and generates a structured markdown document grouped
by logical functionality.

Usage:
    python scripts/generate_codebase_overview.py
    # or via justfile:
    just overview
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
PYPRLAND_DIR = PROJECT_ROOT / "src" / "pyprland"
OUTPUT_FILE = PROJECT_ROOT / "CODEBASE_OVERVIEW.md"

# Minimum docstring length to be considered "good"
MIN_GOOD_DOCSTRING_LEN = 50


@dataclass
class ModuleInfo:
    """Information extracted from a Python module."""

    path: Path
    relative_path: str
    docstring: str | None
    exports: list[str] = field(default_factory=list)
    classes: dict[str, str] = field(default_factory=dict)  # name -> docstring

    @property
    def has_good_docstring(self) -> bool:
        """Check if module has a meaningful docstring (>50 chars)."""
        return bool(self.docstring and len(self.docstring.strip()) > MIN_GOOD_DOCSTRING_LEN)

    @property
    def docstring_status(self) -> str:
        """Return status: good, brief, or missing."""
        if not self.docstring:
            return "missing"
        return "good" if self.has_good_docstring else "brief"


# Logical groupings for core modules
CORE_GROUPINGS: dict[str, list[str]] = {
    "Entry Points & CLI": [
        "command.py",
        "client.py",
        "pypr_daemon.py",
        "help.py",
    ],
    "Configuration": [
        "config.py",
        "config_loader.py",
        "validation.py",
        "validate_cli.py",
    ],
    "IPC & Communication": [
        "ipc.py",
        "ipc_paths.py",
        "httpclient.py",
    ],
    "Process & Task Management": [
        "manager.py",
        "process.py",
        "aioops.py",
        "state.py",
    ],
    "Utilities": [
        "utils.py",
        "common.py",
        "terminal.py",
        "ansi.py",
        "debug.py",
        "logging_setup.py",
    ],
    "Types & Models": [
        "models.py",
        "constants.py",
        "version.py",
    ],
    "Shell Integration": [
        "completions.py",
        "command_registry.py",
    ],
}

ADAPTER_GROUPINGS: dict[str, list[str]] = {
    "Core Abstraction": [
        "backend.py",
        "proxy.py",
        "fallback.py",
    ],
    "Compositor Backends": [
        "hyprland.py",
        "niri.py",
        "wayland.py",
        "xorg.py",
    ],
    "Utilities": [
        "menus.py",
        "colors.py",
        "units.py",
    ],
}

PLUGIN_GROUPINGS: dict[str, list[str]] = {
    "Infrastructure": [
        "interface.py",
        "mixins.py",
        "protocols.py",
    ],
    "Window Management": [
        "scratchpads/",
        "expose.py",
        "fetch_client_menu.py",
        "layout_center.py",
        "lost_windows.py",
        "toggle_special.py",
    ],
    "Monitor & Display": [
        "monitors/",
        "shift_monitors.py",
        "magnify.py",
        "toggle_dpms.py",
        "wallpapers/",
    ],
    "Menus & Launchers": [
        "shortcuts_menu.py",
        "menubar.py",
    ],
    "System Integration": [
        "system_notifier.py",
        "fcitx5_switcher.py",
        "workspaces_follow_focus.py",
    ],
}


def parse_module(path: Path) -> ModuleInfo:
    """Parse a Python module and extract docstring, exports, and classes."""
    relative = path.relative_to(PYPRLAND_DIR)

    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError) as e:
        return ModuleInfo(
            path=path,
            relative_path=str(relative),
            docstring=f"# Parse error: {e}",
        )

    # Extract module docstring
    docstring = ast.get_docstring(tree)

    # Extract __all__ exports
    exports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    if isinstance(node.value, ast.List):
                        exports = [elt.value for elt in node.value.elts if isinstance(elt, ast.Constant) and isinstance(elt.value, str)]

    # Extract class docstrings
    classes: dict[str, str] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            class_doc = ast.get_docstring(node)
            if class_doc:
                # Take first line only
                classes[node.name] = class_doc.split("\n")[0]

    return ModuleInfo(
        path=path,
        relative_path=str(relative),
        docstring=docstring,
        exports=exports,
        classes=classes,
    )


def collect_modules() -> dict[str, list[ModuleInfo]]:
    """Collect all modules organized by package."""
    modules: dict[str, list[ModuleInfo]] = {
        "core": [],
        "adapters": [],
        "plugins": [],
    }

    # Core modules
    for py_file in sorted(PYPRLAND_DIR.glob("*.py")):
        if py_file.name != "__pycache__":
            modules["core"].append(parse_module(py_file))

    # Adapters
    adapters_dir = PYPRLAND_DIR / "adapters"
    for py_file in sorted(adapters_dir.glob("*.py")):
        modules["adapters"].append(parse_module(py_file))

    # Plugins (top-level only, subdirs handled separately)
    plugins_dir = PYPRLAND_DIR / "plugins"
    for py_file in sorted(plugins_dir.glob("*.py")):
        modules["plugins"].append(parse_module(py_file))

    return modules


def format_module_row(mod: ModuleInfo) -> str:
    """Format a module as a markdown table row."""
    name = mod.relative_path.replace("\\", "/")
    status_icon = {"good": "✓", "brief": "~", "missing": "✗"}[mod.docstring_status]

    # First line of docstring or status message
    max_desc_len = 80
    if mod.docstring:
        desc = mod.docstring.split("\n")[0][:max_desc_len]
    else:
        desc = "*No docstring*"

    return f"| `{name}` | {status_icon} | {desc} |"


def generate_section(title: str, modules: list[ModuleInfo], groupings: dict[str, list[str]]) -> list[str]:
    """Generate markdown section for a group of modules."""
    lines = [f"## {title}", ""]

    # Track which modules we've included
    included: set[str] = set()

    for group_name, patterns in groupings.items():
        group_modules = []
        for mod in modules:
            filename = Path(mod.relative_path).name
            if filename in patterns or any(filename.startswith(p.rstrip("/")) for p in patterns if p.endswith("/")):
                group_modules.append(mod)
                included.add(mod.relative_path)

        if group_modules:
            lines.append(f"### {group_name}")
            lines.append("")
            lines.append("| Module | Status | Description |")
            lines.append("|--------|--------|-------------|")
            for mod in group_modules:
                lines.append(format_module_row(mod))
            lines.append("")

    # Add ungrouped modules
    ungrouped = [m for m in modules if m.relative_path not in included]
    if ungrouped:
        lines.append("### Other")
        lines.append("")
        lines.append("| Module | Status | Description |")
        lines.append("|--------|--------|-------------|")
        for mod in ungrouped:
            lines.append(format_module_row(mod))
        lines.append("")

    return lines


def generate_coverage_report(all_modules: list[ModuleInfo]) -> list[str]:
    """Generate documentation coverage summary."""
    good = sum(1 for m in all_modules if m.docstring_status == "good")
    brief = sum(1 for m in all_modules if m.docstring_status == "brief")
    missing = sum(1 for m in all_modules if m.docstring_status == "missing")
    total = len(all_modules)

    lines = [
        "## Documentation Coverage",
        "",
        "| Status | Count | Percentage |",
        "|--------|-------|------------|",
        f"| ✓ Good | {good} | {100 * good / total:.0f}% |",
        f"| ~ Brief | {brief} | {100 * brief / total:.0f}% |",
        f"| ✗ Missing | {missing} | {100 * missing / total:.0f}% |",
        f"| **Total** | **{total}** | |",
        "",
    ]

    # List files needing improvement
    needs_work = [m for m in all_modules if m.docstring_status != "good"]
    if needs_work:
        lines.append("### Files Needing Improvement")
        lines.append("")
        for mod in needs_work:
            status = "missing docstring" if not mod.docstring else "brief docstring"
            lines.append(f"- `{mod.relative_path}` - {status}")
        lines.append("")

    return lines


def main() -> int:
    """Generate the codebase overview."""
    print("Collecting modules...")
    modules = collect_modules()

    all_modules = modules["core"] + modules["adapters"] + modules["plugins"]

    print(f"Found {len(all_modules)} modules")

    # Generate document
    lines = [
        "# Pyprland Codebase Overview",
        "",
        "*Auto-generated from module docstrings. Run `just overview` to regenerate.*",
        "",
    ]

    # Coverage report first
    lines.extend(generate_coverage_report(all_modules))

    # Core modules
    lines.extend(generate_section("Core Modules", modules["core"], CORE_GROUPINGS))

    # Adapters
    lines.extend(generate_section("Adapters", modules["adapters"], ADAPTER_GROUPINGS))

    # Plugins
    lines.extend(generate_section("Plugins", modules["plugins"], PLUGIN_GROUPINGS))

    # Write output
    OUTPUT_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {OUTPUT_FILE}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
