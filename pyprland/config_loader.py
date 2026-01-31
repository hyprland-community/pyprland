"""Configuration file loading utilities.

This module handles loading, parsing, and merging TOML/JSON configuration files.
"""

from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from .constants import CONFIG_FILE, OLD_CONFIG_FILE
from .models import PyprError
from .utils import merge

if TYPE_CHECKING:
    import logging

__all__ = ["ConfigLoader"]


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
            fname = Path(os.path.expandvars(config_filename)).expanduser()
            if fname.is_dir():
                return self._load_config_directory(fname)
            return self._load_config_file(str(fname))

        # No filename specified - use defaults
        if Path(OLD_CONFIG_FILE).exists() and not Path(CONFIG_FILE).exists():
            self.log.warning("Consider changing your configuration to TOML format.")

        fname_str = str(Path(os.path.expandvars(CONFIG_FILE)).expanduser())
        config = self._load_config_file(fname_str)

        # Process includes
        for extra_config in list(config.get("pyprland", {}).get("include", [])):
            merge(config, await self._open_config(extra_config))

        return config

    def _load_config_directory(self, directory: Path) -> dict[str, Any]:
        """Load and merge all .toml files from a directory.

        Args:
            directory: Path to directory containing .toml files

        Returns:
            Merged configuration from all files
        """
        config: dict[str, Any] = {}
        for toml_file in sorted(f.name for f in directory.iterdir()):
            if not toml_file.endswith(".toml"):
                continue
            merge(config, self._load_config_file(str(directory / toml_file)))
        return config

    def _load_config_file(self, fname: str) -> dict[str, Any]:
        """Load a single configuration file.

        Supports both TOML (preferred) and legacy JSON formats.

        Args:
            fname: Path to the configuration file

        Returns:
            Configuration dictionary

        Raises:
            PyprError: If file not found or has syntax errors
        """
        fname_path = Path(fname)
        old_config_path = Path(OLD_CONFIG_FILE).expanduser()

        if fname_path.exists():
            self.log.info("Loading %s", fname)
            with fname_path.open("rb") as f:
                try:
                    return tomllib.load(f)
                except tomllib.TOMLDecodeError as e:
                    self.log.critical("Problem reading %s: %s", fname, e)
                    raise PyprError from e

        if old_config_path.exists():
            self.log.info("Loading %s", OLD_CONFIG_FILE)
            with old_config_path.open(encoding="utf-8") as f:
                return cast("dict[str, Any]", json.loads(f.read()))

        self.log.critical("Config file not found! Please create %s", fname)
        raise PyprError
