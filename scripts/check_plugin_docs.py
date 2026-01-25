#!/usr/bin/env python3
"""Check that all plugin config options and commands are documented.

This script verifies that:
1. Each plugin has at least one documentation page (.md file)
2. All config options appear in a <PluginConfig> table (via filter or unfiltered)
3. All commands appear in a <PluginCommands> list

Exit codes:
- 0: Success (warnings are allowed)
- 1: Error (missing plugin pages)
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
SITE_DIR = PROJECT_ROOT / "site"
GENERATED_DIR = SITE_DIR / "generated"

# ANSI colors for terminal output
RED = "\033[0;31m"
YELLOW = "\033[0;33m"
GREEN = "\033[0;32m"
CYAN = "\033[0;36m"
RESET = "\033[0m"


@dataclass
class PluginCoverage:
    """Coverage information for a single plugin."""

    name: str
    pages: list[str] = field(default_factory=list)
    config_options: list[str] = field(default_factory=list)
    commands: list[str] = field(default_factory=list)
    covered_options: set[str] = field(default_factory=set)
    has_unfiltered_config: bool = False
    has_commands_component: bool = False
    warnings: list[str] = field(default_factory=list)


def load_plugin_json(plugin_name: str) -> dict | None:
    """Load the generated JSON for a plugin."""
    json_path = GENERATED_DIR / f"{plugin_name}.json"
    if not json_path.exists():
        return None
    with open(json_path) as f:
        return json.load(f)


def extract_option_name(full_name: str) -> str:
    """Extract the base option name from a prefixed name.

    E.g., "[scratchpad].command" -> "command"
    """
    match = re.match(r"^\[.*?\]\.(.+)$", full_name)
    return match.group(1) if match else full_name


def find_plugin_pages(plugin_name: str) -> list[Path]:
    """Find all markdown pages that document a plugin.

    Scans for <PluginConfig plugin="X"> or <PluginCommands plugin="X">.
    """
    pages = []
    pattern = re.compile(
        rf'<Plugin(?:Config|Commands)\s+plugin=["\']?{re.escape(plugin_name)}["\']?',
        re.IGNORECASE,
    )

    for md_file in SITE_DIR.glob("*.md"):
        content = md_file.read_text()
        if pattern.search(content):
            pages.append(md_file)

    return pages


def parse_filter_from_component(content: str, plugin_name: str) -> tuple[bool, set[str]]:
    """Parse PluginConfig components and extract filter information.

    Returns:
        Tuple of (has_unfiltered, covered_options)
        - has_unfiltered: True if any PluginConfig has no filter (covers all options)
        - covered_options: Set of option names from :filter arrays
    """
    has_unfiltered = False
    covered_options: set[str] = set()

    # Pattern to match <PluginConfig plugin="X" ... />
    # We need to handle both with and without :filter
    component_pattern = re.compile(rf'<PluginConfig\s+plugin=["\']?{re.escape(plugin_name)}["\']?([^>]*)/?>', re.IGNORECASE | re.DOTALL)

    for match in component_pattern.finditer(content):
        attrs = match.group(1)

        # Check if there's a :filter attribute
        filter_match = re.search(r':filter="\[([^\]]*)\]"', attrs)
        if filter_match:
            # Extract option names from the filter array
            filter_content = filter_match.group(1)
            # Parse the array items (they're quoted strings)
            options = re.findall(r"['\"]([^'\"]+)['\"]", filter_content)
            covered_options.update(options)
        else:
            # No filter means all options are covered
            has_unfiltered = True

    return has_unfiltered, covered_options


def check_commands_component(content: str, plugin_name: str) -> bool:
    """Check if the page has a PluginCommands component for this plugin."""
    pattern = re.compile(rf'<PluginCommands\s+plugin=["\']?{re.escape(plugin_name)}["\']?', re.IGNORECASE)
    return bool(pattern.search(content))


def analyze_plugin(plugin_name: str) -> PluginCoverage:
    """Analyze documentation coverage for a plugin."""
    coverage = PluginCoverage(name=plugin_name)

    # Load plugin data
    data = load_plugin_json(plugin_name)
    if not data:
        coverage.warnings.append(f"No generated JSON found for plugin: {plugin_name}")
        return coverage

    # Extract config options and commands
    coverage.config_options = [extract_option_name(opt["name"]) for opt in data.get("config", [])]
    coverage.commands = [cmd["name"] for cmd in data.get("commands", [])]

    # Find documentation pages
    pages = find_plugin_pages(plugin_name)
    coverage.pages = [p.name for p in pages]

    if not pages:
        coverage.warnings.append(f"No documentation page found for plugin: {plugin_name}")
        return coverage

    # Analyze each page for coverage
    for page in pages:
        content = page.read_text()

        # Check config coverage
        has_unfiltered, options = parse_filter_from_component(content, plugin_name)
        if has_unfiltered:
            coverage.has_unfiltered_config = True
        coverage.covered_options.update(options)

        # Check commands coverage
        if check_commands_component(content, plugin_name):
            coverage.has_commands_component = True

    # Generate warnings for missing items
    if coverage.config_options:
        if not coverage.has_unfiltered_config:
            missing_options = set(coverage.config_options) - coverage.covered_options
            for opt in sorted(missing_options):
                coverage.warnings.append(f"Config option '{opt}' not listed in any table")

    if coverage.commands and not coverage.has_commands_component:
        coverage.warnings.append("Commands not listed (no <PluginCommands> component found)")

    return coverage


def discover_plugins() -> list[str]:
    """Discover all plugins from generated JSON files."""
    plugins = []
    for json_file in GENERATED_DIR.glob("*.json"):
        name = json_file.stem
        # Skip special files
        if name in ("index", "menu", "builtins"):
            continue
        plugins.append(name)
    return sorted(plugins)


def main() -> int:
    """Main entry point."""
    print(f"{CYAN}Checking plugin documentation coverage...{RESET}\n")

    plugins = discover_plugins()
    if not plugins:
        print(f"{RED}No plugins found in {GENERATED_DIR}{RESET}")
        return 1

    total_warnings = 0
    missing_pages = 0
    results: list[PluginCoverage] = []

    for plugin_name in plugins:
        coverage = analyze_plugin(plugin_name)
        results.append(coverage)

        # Print results for this plugin
        print(f"{CYAN}{plugin_name}:{RESET}")

        if coverage.pages:
            print(f"  Pages: {', '.join(coverage.pages)}")
        else:
            print(f"  {RED}Pages: NONE{RESET}")
            missing_pages += 1

        # Config status
        if coverage.config_options:
            if coverage.has_unfiltered_config:
                print(f"  {GREEN}Config: {len(coverage.config_options)}/{len(coverage.config_options)} options covered (unfiltered){RESET}")
            else:
                covered_count = len(coverage.covered_options & set(coverage.config_options))
                total_count = len(coverage.config_options)
                if covered_count == total_count:
                    print(f"  {GREEN}Config: {covered_count}/{total_count} options covered{RESET}")
                else:
                    print(f"  {YELLOW}Config: {covered_count}/{total_count} options covered{RESET}")
        else:
            print("  Config: No config options")

        # Commands status
        if coverage.commands:
            if coverage.has_commands_component:
                print(f"  {GREEN}Commands: {len(coverage.commands)}/{len(coverage.commands)} commands covered{RESET}")
            else:
                print(f"  {YELLOW}Commands: 0/{len(coverage.commands)} commands covered{RESET}")
        else:
            print("  Commands: No commands")

        # Print warnings
        for warning in coverage.warnings:
            print(f"  {YELLOW}[WARN] {warning}{RESET}")
            total_warnings += 1

        print()

    # Summary
    print(f"{CYAN}Summary:{RESET}")
    print(f"  Plugins checked: {len(plugins)}")
    print(f"  Warnings: {total_warnings}")
    print(f"  Missing pages: {missing_pages}")

    if missing_pages > 0:
        print(f"\n{RED}FAILED: Some plugins have no documentation page{RESET}")
        return 1

    if total_warnings > 0:
        print(f"\n{YELLOW}PASSED with warnings{RESET}")
    else:
        print(f"\n{GREEN}PASSED{RESET}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
