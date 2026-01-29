"""Configuration wrapper providing typed access and section filtering."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, overload

if TYPE_CHECKING:
    import logging
    from collections.abc import Iterator

    from .validation import ConfigItems

__all__ = ["Configuration", "SchemaAwareMixin", "coerce_to_bool", "BOOL_TRUE_STRINGS", "BOOL_FALSE_STRINGS", "BOOL_STRINGS"]

# Type alias for config values
ConfigValueType = float | bool | str | list | dict

# Boolean string constants (shared with validation module)
BOOL_TRUE_STRINGS = frozenset({"true", "yes", "on", "1", "enabled"})
BOOL_FALSE_STRINGS = frozenset({"false", "no", "off", "0", "disabled"})
BOOL_STRINGS = BOOL_TRUE_STRINGS | BOOL_FALSE_STRINGS


def coerce_to_bool(value: ConfigValueType | None, default: bool = False) -> bool:
    """Coerce a value to boolean, handling loose typing.

    Args:
        value: The value to coerce
        default: Default value if value is None

    Returns:
        The boolean value

    Behavior:
        - None → default
        - Empty string → False
        - Explicit falsy strings ("false", "no", "off", "0", "disabled") → False
        - Any other non-empty string → True
        - Non-string values → bool(value)
    """
    if value is None:
        return default
    if isinstance(value, str):
        if not value.strip():
            return False
        return value.lower().strip() not in BOOL_FALSE_STRINGS
    return bool(value)


class SchemaAwareMixin:
    """Mixin providing schema-aware defaults and typed config value accessors.

    Requires the implementing class to have:
    - self._get_raw(name) method that returns the raw value or raises KeyError
    - self.log (logging.Logger) attribute

    Provides:
    - Schema default value storage and lookup
    - Typed accessors: get_bool, get_int, get_float, get_str
    - Schema-aware get() method
    """

    _schema_defaults: dict[str, ConfigValueType]

    def __init_schema__(self) -> None:
        """Initialize schema defaults storage. Call from subclass __init__."""
        self._schema_defaults = {}

    def set_schema(self, schema: ConfigItems) -> None:
        """Set or update the schema for default value lookups.

        Args:
            schema: List of ConfigField definitions
        """
        self._schema_defaults = {field.name: field.default for field in schema if field.default is not None}

    def _get_raw(self, name: str) -> ConfigValueType:
        """Get raw value without defaults. Raises KeyError if not found.

        Override in subclasses to provide the actual lookup mechanism.
        """
        raise NotImplementedError

    @overload
    def get(self, name: str) -> ConfigValueType | None: ...

    @overload
    def get(self, name: str, default: None) -> ConfigValueType | None: ...

    @overload
    def get(self, name: str, default: ConfigValueType) -> ConfigValueType: ...

    def get(self, name: str, default: ConfigValueType | None = None) -> ConfigValueType | None:
        """Get a value with schema-aware defaults.

        Args:
            name: The configuration key
            default: Fallback if key is missing and not in schema defaults

        Returns:
            The value, schema default, or provided default
        """
        try:
            return self._get_raw(name)
        except KeyError:
            if name in self._schema_defaults:
                return self._schema_defaults[name]
            return default

    def get_bool(self, name: str, default: bool = False) -> bool:
        """Get a boolean value, handling loose typing.

        Args:
            name: The key name
            default: Default value if key is missing

        Returns:
            The boolean value

        Behavior:
            - None (missing key) → default
            - Empty string → False
            - Explicit falsy strings ("false", "no", "off", "0", "disabled") → False
            - Any other non-empty string → True
            - Non-string values → bool(value)
        """
        return coerce_to_bool(self.get(name), default)

    def get_int(self, name: str, default: int = 0) -> int:
        """Get an integer value.

        Args:
            name: The key name
            default: Default value if key is missing or invalid

        Returns:
            The integer value
        """
        value = self.get(name)
        if value is None:
            return default
        try:
            return int(value)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            self.log.warning("Invalid integer value for %s: %s", name, value)  # type: ignore[attr-defined]
            return default

    def get_float(self, name: str, default: float = 0.0) -> float:
        """Get a float value.

        Args:
            name: The key name
            default: Default value if key is missing or invalid

        Returns:
            The float value
        """
        value = self.get(name)
        if value is None:
            return default
        try:
            return float(value)  # type: ignore[arg-type]
        except (ValueError, TypeError):
            self.log.warning("Invalid float value for %s: %s", name, value)  # type: ignore[attr-defined]
            return default

    def get_str(self, name: str, default: str = "") -> str:
        """Get a string value.

        Args:
            name: The key name
            default: Default value if key is missing

        Returns:
            The string value
        """
        value = self.get(name)
        if value is None:
            return default
        return str(value)

    def has_explicit(self, name: str) -> bool:
        """Check if value was explicitly set (not from schema default).

        Args:
            name: The configuration key

        Returns:
            True if the value exists in the raw config (not from schema defaults)
        """
        try:
            self._get_raw(name)
        except KeyError:
            return False
        return True


class Configuration(SchemaAwareMixin, dict):
    """Configuration wrapper providing typed access and section filtering.

    Optionally accepts a schema to provide default values automatically.
    """

    def __init__(
        self,
        *args: Any,  # noqa: ANN401
        logger: logging.Logger,
        schema: ConfigItems | None = None,
        **kwargs: Any,  # noqa: ANN401
    ):
        """Initialize the configuration object.

        Args:
            *args: Arguments for dict
            logger: Logger instance to use for warnings
            schema: Optional list of ConfigField definitions for automatic defaults
            **kwargs: Keyword arguments for dict
        """
        super().__init__(*args, **kwargs)
        self.__init_schema__()
        self.log = logger
        if schema:
            self.set_schema(schema)

    def _get_raw(self, name: str) -> ConfigValueType:
        """Get raw value from dict. Raises KeyError if not found."""
        if name in self:
            return dict.get(self, name)  # type: ignore[return-value]
        raise KeyError(name)

    def get(self, name: str, default: ConfigValueType | None = None) -> ConfigValueType | None:  # type: ignore[override]
        """Get a value with schema-aware defaults.

        Args:
            name: The configuration key
            default: Fallback if key is missing and not in schema defaults

        Returns:
            The value, schema default, or provided default
        """
        return SchemaAwareMixin.get(self, name, default)

    def iter_subsections(self) -> Iterator[tuple[str, dict[str, Any]]]:
        """Yield only keys that have dictionary values (e.g., defined scratchpads).

        Returns:
            Iterator of (key, value) pairs where value is a dictionary
        """
        for k, v in self.items():
            if isinstance(v, dict):
                yield k, v
