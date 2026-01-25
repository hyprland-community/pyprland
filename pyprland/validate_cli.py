"""CLI validation entry point for pyprland configuration."""

import importlib
import json
import logging
import os
import sys
import tomllib
from typing import cast

from .common import get_logger, merge
from .constants import CONFIG_FILE, OLD_CONFIG_FILE
from .models import ExitCode
from .plugins.interface import Plugin
from .validation import ConfigItems, ConfigValidator

__all__ = ["run_validate"]


def _load_plugin_module(name: str) -> type[Plugin] | None:
    """Load a plugin module and return its Extension class.

    Args:
        name: Plugin name

    Returns:
        The Extension class or None if not found
    """
    for module_path in [f"pyprland.plugins.{name}", name]:
        try:
            module = importlib.import_module(module_path)
            return cast("type", module.Extension)
        except (ModuleNotFoundError, AttributeError):
            continue
    return None


def _load_validate_config(log: logging.Logger) -> dict:
    """Load config file for validation.

    Args:
        log: Logger instance

    Returns:
        Loaded configuration dictionary
    """
    filename = os.path.expanduser(CONFIG_FILE)
    old_filename = os.path.expanduser(OLD_CONFIG_FILE)

    if os.path.exists(filename):
        with open(filename, "rb") as f:
            config = tomllib.load(f)
        log.info("Loaded config from %s", filename)
        return config

    if os.path.exists(old_filename):
        with open(old_filename, encoding="utf-8") as f:
            config = cast("dict", json.loads(f.read()))
        log.info("Loaded config from %s (consider migrating to TOML)", old_filename)
        return config

    log.error("Config file not found at %s", filename)
    sys.exit(ExitCode.ENV_ERROR)


def _validate_plugin(plugin_name: str, config: dict) -> tuple[int, int]:
    """Validate a single plugin's configuration.

    Args:
        plugin_name: Name of the plugin
        config: Full configuration dictionary

    Returns:
        Tuple of (error_count, warning_count)
    """
    extension_class = _load_plugin_module(plugin_name)
    if extension_class is None:
        get_logger("validate").warning("Plugin '%s' not found, skipping validation", plugin_name)
        return (0, 0)

    plugin_config = config.get(plugin_name, {})
    schema: ConfigItems = cast("ConfigItems", getattr(extension_class, "config_schema", ConfigItems()))

    # Check if plugin has validation capability
    has_schema = bool(schema)
    has_custom_validation = "validate_config_static" in vars(extension_class)

    if not has_schema and not has_custom_validation:
        print(f"∅  [{plugin_name}] skipped")
        return (0, 0)

    # Get errors from class-level validation
    errors = extension_class.validate_config_static(plugin_name, plugin_config)

    # Get warnings for unknown keys (only if schema exists)
    warnings: list[str] = []
    if schema:
        silent_logger = logging.getLogger(f"pyprland.validate.{plugin_name}")
        silent_logger.addHandler(logging.NullHandler())
        silent_logger.propagate = False
        validator = ConfigValidator(plugin_config, plugin_name, silent_logger)
        warnings = validator.warn_unknown_keys(schema)

    if errors or warnings:
        print(f"  [{plugin_name}]")
        for error in errors:
            print(f"  ERROR: {error}")
        for warning in warnings:
            print(f"  WARNING: {warning}")
    else:
        print(f"✅ [{plugin_name}]")

    return (len(errors), len(warnings))


def run_validate() -> None:
    """Validate the configuration file without starting the daemon.

    Checks all plugin configurations against their schemas and reports errors.
    """
    log = get_logger("validate")
    config = _load_validate_config(log)

    # Validate pyprland section exists
    if "pyprland" not in config:
        log.error("Config must have a [pyprland] section")
        sys.exit(ExitCode.USAGE_ERROR)

    pyprland_config = config["pyprland"]
    if "plugins" not in pyprland_config:
        log.error("Config must have 'plugins' list in [pyprland] section")
        sys.exit(ExitCode.USAGE_ERROR)

    extra_include = pyprland_config.get("include", [])
    for extra_config in extra_include:
        fname = os.path.expanduser(os.path.expandvars(extra_config))
        if os.path.isdir(fname):
            extra_include.extend(os.path.join(fname, f) for f in os.listdir(fname) if f.endswith(".toml"))
        else:
            doc = {}
            with open(fname, "rb") as toml_file:
                doc.update(tomllib.load(toml_file))
            if doc:
                merge(config, doc)

    plugins = sorted(set(config["pyprland"]["plugins"]))
    print(f"Validating configuration for {len(plugins)} plugin(s)...\n")

    total_errors = 0
    total_warnings = 0
    for plugin_name in plugins:
        errors, warnings = _validate_plugin(plugin_name, config)
        total_errors += errors
        total_warnings += warnings

    # Summary
    print()
    if total_errors == 0 and total_warnings == 0:
        print("Configuration is valid!")
        sys.exit(ExitCode.SUCCESS)
    elif total_errors > 0:
        print(f"Found {total_errors} error(s) and {total_warnings} warning(s)")
        sys.exit(ExitCode.USAGE_ERROR)
    else:
        print(f"Found {total_warnings} warning(s)")
        sys.exit(ExitCode.SUCCESS)
