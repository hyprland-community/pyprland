"""Common plugin interface."""

import contextlib
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from ..adapters.proxy import BackendProxy
from ..common import SharedState, get_logger
from ..config import Configuration, coerce_to_bool
from ..models import ClientInfo, MonitorInfo
from ..validation import ConfigItems, ConfigValidator

if TYPE_CHECKING:
    from ..manager import Pyprland

ConfigValue = int | float | str | list[Any] | dict[Any, Any]
"""Type alias for values returned by get_config."""


@dataclass
class PluginContext:
    """Context from a plugin, for use by helper classes.

    Groups the commonly needed plugin attributes (log, state, backend)
    to reduce instance attribute count in helper classes.
    """

    log: logging.Logger
    state: SharedState
    backend: BackendProxy


class Plugin:
    """Base class for any pyprland plugin.

    Configuration Access:
        Use the typed accessor methods for reading configuration values:
        - get_config_str(name) - for string values
        - get_config_int(name) - for integer values
        - get_config_float(name) - for float values
        - get_config_bool(name) - for boolean values
        - get_config_list(name) - for list values
        - get_config_dict(name) - for dict values

        All config keys must be defined in config_schema for validation and defaults.
    """

    aborted = False

    environments: ClassVar[list[str]] = []
    " The supported environments for this plugin. Empty list means all environments. "

    backend: BackendProxy
    " The environment backend "

    manager: "Pyprland | None"
    " Reference to the plugin manager (set for pyprland plugin only) "

    config_schema: ConfigItems
    """Schema defining expected configuration fields. Override in subclasses to enable validation."""

    def get_config(self, name: str) -> ConfigValue:
        """Get a configuration value by name.

        Args:
            name: Configuration key name (must be defined in config_schema)

        Returns:
            The configuration value

        Raises:
            KeyError: If the key is not defined in config_schema
        """
        # Configuration.get() already handles schema defaults via set_schema()
        value = self.config.get(name)

        if value is not None:
            return value

        # Value is None - need schema for type-appropriate default
        schema = self.config_schema.get(name)
        if not schema:
            msg = f"Unknown config key '{name}' - not defined in config_schema"
            raise KeyError(msg)

        first_type = schema.field_type[0] if isinstance(schema.field_type, (list, tuple)) else schema.field_type
        return first_type()  # type: ignore[no-any-return]

    def get_config_str(self, name: str) -> str:
        """Get a string configuration value by name."""
        return str(self.get_config(name))

    def get_config_int(self, name: str) -> int:
        """Get an integer configuration value by name.

        Args:
            name: Configuration key name

        Returns:
            The integer value, or 0 if conversion fails
        """
        value = self.get_config(name)
        try:
            return int(value)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            self.log.warning("Invalid integer value for %s: %s, using 0", name, value)
            return 0

    def get_config_float(self, name: str) -> float:
        """Get a float configuration value by name.

        Args:
            name: Configuration key name

        Returns:
            The float value, or 0.0 if conversion fails
        """
        value = self.get_config(name)
        try:
            return float(value)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            self.log.warning("Invalid float value for %s: %s, using 0.0", name, value)
            return 0.0

    def get_config_bool(self, name: str) -> bool:
        """Get a boolean configuration value by name.

        Handles loose typing: strings like "false", "no", "off", "0", "disabled"
        are treated as False.
        """
        return coerce_to_bool(self.get_config(name))

    def get_config_list(self, name: str) -> list[Any]:
        """Get a list configuration value by name."""
        result = self.get_config(name)
        assert isinstance(result, list), f"Expected list for {name}, got {type(result)}"
        return result

    def get_config_dict(self, name: str) -> dict[str, Any]:
        """Get a dict configuration value by name."""
        result = self.get_config(name)
        assert isinstance(result, dict), f"Expected dict for {name}, got {type(result)}"
        return result

    config: Configuration
    " This plugin configuration section as a `dict` object "

    state: SharedState
    " The shared state object "

    def __init__(self, name: str) -> None:
        """Create a new plugin `name` and the matching logger."""
        self.name = name
        """ the plugin name """
        if not hasattr(self, "config_schema"):
            self.config_schema = ConfigItems()
        self.log = get_logger(name)
        """ the logger to use for this plugin """
        self.config = Configuration({}, logger=self.log)
        self.manager = None

    # Functions to override

    async def init(self) -> None:
        """Initialize the plugin.

        Note that the `config` attribute isn't ready yet when this is called.
        """

    async def on_reload(self) -> None:
        """Add the code which requires the `config` attribute here.

        This is called on *init* and *reload*
        """

    async def exit(self) -> None:
        """Empty exit function."""

    # Generic implementations

    async def load_config(self, config: dict[str, Any]) -> None:
        """Load the configuration section from the passed `config`."""
        self.config.clear()
        with contextlib.suppress(KeyError):
            self.config.update(config[self.name])
        # Apply schema for default value lookups
        if self.config_schema:
            self.config.set_schema(self.config_schema)

    def validate_config(self) -> list[str]:
        """Validate the current configuration against the schema.

        Override config_schema in subclasses to define expected fields.
        Validation runs automatically during plugin loading if schema is defined.

        Returns:
            List of validation error messages (empty if valid)
        """
        if not self.config_schema:
            return []

        validator = ConfigValidator(self.config, self.name, self.log)
        errors = validator.validate(self.config_schema)
        validator.warn_unknown_keys(self.config_schema)
        return errors

    @classmethod
    def validate_config_static(cls, plugin_name: str, config: dict) -> list[str]:
        """Validate configuration without instantiating the plugin.

        Override in subclasses for custom validation logic.
        Called by 'pypr validate' CLI command.

        Args:
            plugin_name: Name of the plugin (for error messages)
            config: The plugin's configuration dict

        Returns:
            List of validation error messages (empty if valid)
        """
        if not cls.config_schema:
            return []
        log = logging.getLogger(f"pyprland.plugins.{plugin_name}")
        validator = ConfigValidator(config, plugin_name, log)
        return validator.validate(cls.config_schema)

    async def get_clients(
        self,
        mapped: bool = True,
        workspace: None | str = None,
        workspace_bl: str | None = None,
    ) -> list[ClientInfo]:
        """Return the client list, optionally returns only mapped clients or from a given workspace.

        Args:
            mapped: Filter for mapped clients
            workspace: Filter for specific workspace name
            workspace_bl: Filter to blacklist a specific workspace name
        """
        return await self.backend.get_clients(mapped, workspace, workspace_bl)

    async def get_focused_monitor_or_warn(self, context: str = "") -> MonitorInfo | None:
        """Get the focused monitor, logging a warning if none found.

        This is a common helper to reduce repeated try/except patterns
        for RuntimeError when calling get_monitor_props().

        Args:
            context: Optional context for the warning message (e.g., "centered layout")

        Returns:
            MonitorInfo if found, None otherwise
        """
        try:
            return await self.backend.get_monitor_props()
        except RuntimeError:
            msg = "No focused monitor found"
            if context:
                msg = f"{msg} for {context}"
            self.log.warning(msg)
            return None
