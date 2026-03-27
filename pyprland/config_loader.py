"""Configuration file loading utilities.

This module handles loading, parsing, and merging TOML/JSON configuration files.

The module-level functions :func:`resolve_config_path`, :func:`load_toml`,
:func:`load_toml_directory`, and :func:`load_config` are the shared
primitives used by both the daemon (``ConfigLoader``) and the GUI
(``pyprland.gui.api``).
"""

from __future__ import annotations

import json
import logging
import os
import tomllib
from pathlib import Path
from typing import Any, cast

from .aioops import aiexists, aiisdir
from .constants import CONFIG_FILE, LEGACY_CONFIG_FILE, MIGRATION_NOTIFICATION_DURATION_MS, OLD_CONFIG_FILE
from .models import PyprError
from .utils import merge

__all__ = [
    "ConfigLoader",
    "load_config",
    "load_toml",
    "load_toml_directory",
    "resolve_config_path",
]

_log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Shared primitives (used by both the daemon and the GUI)
# ---------------------------------------------------------------------------


def resolve_config_path(config_filename: str) -> Path:
    """Resolve a config filename with variable and user expansion.

    Args:
        config_filename: Raw config file path (may contain ``$VARS`` or ``~``)

    Returns:
        Resolved Path object
    """
    return Path(os.path.expandvars(config_filename)).expanduser()


def load_toml(path: Path) -> dict[str, Any]:
    """Load a single TOML file, returning ``{}`` on error.

    Unlike :meth:`ConfigLoader._load_config_file` this never raises and
    has no legacy JSON fallback — it is meant for best-effort loading.
    """
    try:
        with path.open("rb") as fh:
            return tomllib.load(fh)
    except Exception:  # noqa: BLE001
        _log.warning("Failed to load %s", path, exc_info=True)
        return {}


def load_toml_directory(directory: Path) -> dict[str, Any]:
    """Load and merge all ``.toml`` files in *directory* (sorted)."""
    config: dict[str, Any] = {}
    if not directory.is_dir():
        return config
    for name in sorted(f.name for f in directory.iterdir() if f.suffix == ".toml"):
        merge(config, load_toml(directory / name))
    return config


def load_config(config_filename: str | None = None) -> dict[str, Any]:
    """Synchronously load config, recursively resolving includes.

    Mirrors the daemon's :meth:`ConfigLoader._open_config` logic so that
    any caller gets the same merged result as ``pypr dumpjson``.

    When *config_filename* is given it is treated as an include path (may
    be a file or a directory).  When ``None`` the default config path is
    used and its ``pyprland.include`` entries are resolved recursively.
    """
    if config_filename is not None:
        resolved = resolve_config_path(config_filename)
        if resolved.is_dir():
            return load_toml_directory(resolved)
        return load_toml(resolved)

    # Default: load the main config and recursively resolve includes
    from .quickstart.generator import get_config_path  # noqa: PLC0415

    config_path = get_config_path()
    config = load_toml(config_path) if config_path.exists() else {}

    for extra in list(config.get("pyprland", {}).get("include", [])):
        merge(config, load_config(extra))

    return config


# ---------------------------------------------------------------------------
#  ConfigLoader — daemon-specific wrapper with async, logging, legacy fallback
# ---------------------------------------------------------------------------


class ConfigLoader:
    """Handles loading and merging configuration files.

    Supports:
    - TOML configuration files (preferred)
    - Legacy JSON configuration files
    - Directory-based config (multiple .toml files merged)
    - Include directives for modular configuration
    """

    def __init__(self, log: logging.Logger) -> None:
        """Initialize the config loader.

        Args:
            log: Logger instance for status and error messages
        """
        self.log = log
        self._config: dict[str, Any] = {}
        self.deferred_notifications: list[tuple[str, int]] = []

    @property
    def config(self) -> dict[str, Any]:
        """Return the loaded configuration."""
        return self._config

    async def load(self, config_filename: str = "") -> dict[str, Any]:
        """Load configuration from file or directory.

        Args:
            config_filename: Optional path to config file or directory.
                           If empty, uses default CONFIG_FILE location.

        Returns:
            The loaded and merged configuration dictionary.

        Raises:
            PyprError: If config file not found or has syntax errors.
        """
        config = await self._open_config(config_filename)
        merge(self._config, config, replace=True)
        return self._config

    async def _open_config(self, config_filename: str = "") -> dict[str, Any]:
        """Load config file(s) into a dictionary.

        Args:
            config_filename: Optional configuration file or directory path

        Returns:
            The loaded configuration dictionary
        """
        if config_filename:
            fname = resolve_config_path(config_filename)
            if await aiisdir(str(fname)):
                return self._load_config_directory(fname)
            return self._load_config_file(fname)

        # No filename specified - use defaults with legacy fallback
        config_path = CONFIG_FILE
        legacy_path = LEGACY_CONFIG_FILE
        old_json_path = OLD_CONFIG_FILE

        if await aiexists(config_path):
            # New canonical location
            fname = config_path
        elif await aiexists(legacy_path):
            # Legacy TOML location - use it but warn user
            fname = legacy_path
            self.log.warning("Using legacy config path: %s", legacy_path)
            self.log.warning("Please move your config to: %s", config_path)
            self.deferred_notifications.append(
                (
                    f"Config at legacy location.\nMove to: {config_path}",
                    MIGRATION_NOTIFICATION_DURATION_MS,
                )
            )
        elif await aiexists(old_json_path):
            # Very old JSON format - will be loaded via fallback in _load_config_file
            self.log.warning("Using deprecated JSON config: %s", old_json_path)
            self.log.warning("Please migrate to TOML format at: %s", config_path)
            self.deferred_notifications.append(
                (
                    f"JSON config is deprecated.\nMigrate to: {config_path}",
                    MIGRATION_NOTIFICATION_DURATION_MS,
                )
            )
            fname = config_path  # Will fall through to JSON loading in _load_config_file
        else:
            fname = config_path  # Will error in _load_config_file

        config = self._load_config_file(fname)

        # Process includes
        for extra_config in list(config.get("pyprland", {}).get("include", [])):
            merge(config, await self._open_config(extra_config))

        return config

    def _load_config_directory(self, directory: Path) -> dict[str, Any]:
        """Load and merge all .toml files from a directory.

        Delegates to :func:`load_toml_directory` but uses
        :meth:`_load_config_file` (which raises on errors) for each file.
        """
        config: dict[str, Any] = {}
        for toml_file in sorted(f.name for f in directory.iterdir()):
            if not toml_file.endswith(".toml"):
                continue
            merge(config, self._load_config_file(directory / toml_file))
        return config

    def _load_config_file(self, fname: Path) -> dict[str, Any]:
        """Load a single configuration file.

        Supports both TOML (preferred) and legacy JSON formats.

        Args:
            fname: Path to the configuration file

        Returns:
            Configuration dictionary

        Raises:
            PyprError: If file not found or has syntax errors
        """
        if fname.exists():
            self.log.info("Loading %s", fname)
            with fname.open("rb") as f:
                try:
                    return tomllib.load(f)
                except tomllib.TOMLDecodeError as e:
                    self.log.critical("Problem reading %s: %s", fname, e)
                    raise PyprError from e

        # Fallback to very old JSON config
        if OLD_CONFIG_FILE.exists():
            self.log.info("Loading %s", OLD_CONFIG_FILE)
            with OLD_CONFIG_FILE.open(encoding="utf-8") as f:
                return cast("dict[str, Any]", json.loads(f.read()))

        self.log.critical("Config file not found! Please create %s", fname)
        raise PyprError
