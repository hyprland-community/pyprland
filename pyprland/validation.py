"""Configuration validation framework."""

import difflib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, cast

from .config import BOOL_STRINGS

__all__ = [
    "ConfigField",
    "ConfigValidator",
    "format_config_error",
]


@dataclass
class ConfigField:
    """Describes an expected configuration field for validation.

    Attributes:
        name: The configuration key name
        field_type: Expected type (str, int, float, bool, list, dict) or tuple of types for union
        required: Whether the field is required
        recommended: Whether the field is recommended (but not required)
        default: Default value if not provided
        description: Human-readable description for error messages
        choices: List of valid values for enum-like fields
    """

    name: str
    field_type: type | tuple[type, ...] = str
    required: bool = False
    recommended: bool = False
    default: Any = None
    description: str = ""
    choices: list | None = None
    validator: Callable[[Any], list[str]] | None = None

    @property
    def type_name(self) -> str:
        """Return human-readable type name (e.g., 'str', 'int or str')."""
        if isinstance(self.field_type, tuple):
            return " or ".join(t.__name__ for t in self.field_type)
        return self.field_type.__name__


class ConfigItems(list):
    """A list of ConfigField items with cached lookup by name."""

    def __init__(self, *args: ConfigField):
        super().__init__(args)
        self._cache: dict[str, ConfigField] = {}

    def get(self, name: str) -> ConfigField | None:
        """Get a ConfigField by name, with caching for repeated lookups.

        Args:
            name: The field name to look up

        Returns:
            The ConfigField if found, None otherwise
        """
        v = self._cache.get(name)
        if not v:
            for prop in self:
                if prop.name == name:
                    v = prop
                    self._cache[name] = v
                    break
        return v


def _find_similar_key(unknown_key: str, known_keys: list[str]) -> str | None:
    """Find a similar key using fuzzy matching.

    Args:
        unknown_key: The unknown key to find a match for
        known_keys: List of valid keys to search

    Returns:
        The closest matching key, or None if no close match found
    """
    matches = difflib.get_close_matches(unknown_key, known_keys, n=1)
    if matches:
        return matches[0]
    return None


def format_config_error(plugin: str, field: str, message: str, suggestion: str = "") -> str:
    """Format a configuration error message.

    Args:
        plugin: Plugin name
        field: Field name that has the error
        message: Error description
        suggestion: Optional suggestion for fixing the error

    Returns:
        Formatted error message
    """
    msg = f"[{plugin}] Config error for '{field}': {message}"
    if suggestion:
        msg += f" -> {suggestion}"
    return msg


class ConfigValidator:
    """Validates configuration against a schema."""

    def __init__(self, config: dict, plugin_name: str, logger: logging.Logger):
        """Initialize the validator.

        Args:
            config: The configuration dictionary to validate
            plugin_name: Name of the plugin for error messages
            logger: Logger instance for warnings
        """
        self.config = config
        self.plugin_name = plugin_name
        self.log = logger

    def validate(self, schema: ConfigItems) -> list[str]:
        """Validate configuration against schema.

        Args:
            schema: List of ConfigField definitions

        Returns:
            List of error messages (empty if validation passed)
        """
        errors = []

        for field_def in schema:
            value = self.config.get(field_def.name)

            # Check required fields
            if field_def.required and value is None:
                suggestion = self._get_required_suggestion(field_def)
                errors.append(
                    format_config_error(
                        self.plugin_name,
                        field_def.name,
                        "Missing required field",
                        suggestion,
                    )
                )
                continue

            # Skip optional fields that aren't set
            if value is None:
                continue

            # Check type
            type_error = self._check_type(field_def, value)
            if type_error:
                errors.append(type_error)
                continue

            # Check choices (skip if custom validator handles validation)
            if field_def.choices is not None and field_def.validator is None and value not in field_def.choices:
                choices_str = ", ".join(repr(c) for c in field_def.choices)
                errors.append(
                    format_config_error(
                        self.plugin_name,
                        field_def.name,
                        f"Invalid value {value!r}",
                        f"Valid options: {choices_str}",
                    )
                )
            # custom validation
            if field_def.validator:
                errors.extend(
                    format_config_error(
                        self.plugin_name,
                        field_def.name,
                        validation_error,
                    )
                    for validation_error in field_def.validator(value)
                )

        return errors

    def _check_type(self, field_def: ConfigField, value: Any) -> str | None:  # noqa: ANN401
        """Check if value matches expected type.

        Args:
            field_def: Field definition
            value: Value to check

        Returns:
            Error message if type mismatch, None otherwise
        """
        expected_type = field_def.field_type

        # Handle union types (tuple of types)
        if isinstance(expected_type, tuple):
            return self._check_union_type(field_def, value, expected_type)

        # Dispatch to type-specific checkers
        checkers = {
            bool: self._check_bool,
            int: self._check_numeric,
            float: self._check_numeric,
            str: self._check_str,
            list: self._check_list,
            dict: self._check_dict,
        }

        checker = checkers.get(expected_type)
        if checker:
            return checker(field_def, value)
        return None

    def _check_union_type(
        self,
        field_def: ConfigField,
        value: Any,  # noqa: ANN401
        expected_types: tuple,  # noqa: ANN401
    ) -> str | None:
        """Check if value matches any of the union types."""
        for single_type in expected_types:
            temp_field = ConfigField(field_def.name, single_type)
            if self._check_type(temp_field, value) is None:
                return None
        return format_config_error(
            self.plugin_name,
            field_def.name,
            f"Expected {field_def.type_name}, got {type(value).__name__}",
        )

    def _check_bool(self, field_def: ConfigField, value: Any) -> str | None:  # noqa: ANN401
        """Check bool type (special handling since bool is subclass of int)."""
        if isinstance(value, bool):
            return None
        if isinstance(value, str) and value.lower() in BOOL_STRINGS:
            return None
        return format_config_error(
            self.plugin_name,
            field_def.name,
            f"Expected bool, got {type(value).__name__}",
            "Use true/false (without quotes)",
        )

    def _check_numeric(self, field_def: ConfigField, value: Any) -> str | None:  # noqa: ANN401
        """Check int/float type."""
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return None
        expected_type = cast("type[int | float]", field_def.field_type)
        try:
            expected_type(value)
        except (ValueError, TypeError):
            return format_config_error(
                self.plugin_name,
                field_def.name,
                f"Expected {expected_type.__name__}, got {type(value).__name__}",
                f"Use {field_def.name} = 42 (without quotes)",
            )

        return None

    def _check_str(self, field_def: ConfigField, value: Any) -> str | None:  # noqa: ANN401
        """Check str type."""
        if isinstance(value, str):
            return None
        return format_config_error(
            self.plugin_name,
            field_def.name,
            f"Expected str, got {type(value).__name__}",
            f'Use {field_def.name} = "value"',
        )

    def _check_list(self, field_def: ConfigField, value: Any) -> str | None:  # noqa: ANN401
        """Check list type."""
        if isinstance(value, list):
            return None
        return format_config_error(
            self.plugin_name,
            field_def.name,
            f"Expected list, got {type(value).__name__}",
            f'Use {field_def.name} = ["item1", "item2"]',
        )

    def _check_dict(self, field_def: ConfigField, value: Any) -> str | None:  # noqa: ANN401
        """Check dict type."""
        if isinstance(value, dict):
            return None
        return format_config_error(
            self.plugin_name,
            field_def.name,
            f"Expected dict/section, got {type(value).__name__}",
        )

    def _get_required_suggestion(self, field_def: ConfigField) -> str:
        """Generate suggestion for a missing required field.

        Args:
            field_def: Field definition

        Returns:
            Suggestion string
        """
        field_type = field_def.field_type
        # For union types, use the first type for suggestion
        if isinstance(field_type, tuple):
            field_type = field_type[0]

        if field_type is str:
            return f'Add {field_def.name} = "value" to [{self.plugin_name}]'
        if field_type is int:
            example = field_def.default if field_def.default is not None else 0
            return f"Add {field_def.name} = {example} to [{self.plugin_name}]"
        if field_type is float:
            example = field_def.default if field_def.default is not None else 0.0
            return f"Add {field_def.name} = {example} to [{self.plugin_name}]"
        if field_type is bool:
            return f"Add {field_def.name} = true/false to [{self.plugin_name}]"
        if field_type is list:
            return f'Add {field_def.name} = ["item"] to [{self.plugin_name}]'
        return f"Add '{field_def.name}' to [{self.plugin_name}]"

    def warn_unknown_keys(self, schema: ConfigItems) -> list[str]:
        """Log warnings for unknown configuration keys.

        Args:
            schema: List of ConfigField definitions

        Returns:
            List of warning messages
        """
        warnings = []
        known_keys = {f.name for f in schema}

        for key in self.config:
            if key in known_keys:
                continue

            # Check for similar keys (typos)
            similar = _find_similar_key(key, list(known_keys))
            if similar:
                msg = f"[{self.plugin_name}] Unknown option '{key}' (did you mean '{similar}'?)"
            else:
                msg = f"[{self.plugin_name}] Unknown option '{key}' - will be ignored"

            self.log.warning(msg)
            warnings.append(msg)

        return warnings
