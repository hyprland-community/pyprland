"""Configuration schema for monitors plugin."""

from typing import Any

from ...validation import ConfigField, ConfigItems

# Valid placement directions for custom validator
PLACEMENT_DIRECTIONS = {"left", "right", "top", "bottom"}

# Static monitor properties (used by both schema validation and layout logic)
MONITOR_PROPS = {"resolution", "rate", "scale", "transform"}

# Schema for monitor properties within placement config
MONITOR_PROPS_SCHEMA = ConfigItems(
    ConfigField("scale", float, description="UI scale factor"),
    ConfigField("rate", (int, float), description="Refresh rate in Hz"),
    ConfigField(
        "resolution",
        (str, list),
        description="Display resolution (e.g., '2560x1440' or [2560, 1440])",
    ),
    ConfigField(
        "transform",
        int,
        choices=[0, 1, 2, 3, 4, 5, 6, 7],
        description="Rotation/flip transform",
    ),
    ConfigField(
        "disables",
        list,
        description="List of monitors to disable when this monitor is connected",
    ),
)


def validate_placement_keys(value: dict[str, Any]) -> list[str]:
    """Validator for dynamic placement keys (leftOf, topCenterOf, etc).

    Static properties (scale, rate, resolution, transform, disables) are
    validated by the children schema. This validator handles the dynamic
    placement direction rules.

    Args:
        value: The placement configuration dictionary

    Returns:
        List of validation errors
    """
    errors = []
    # Get known static property names from schema
    known_props = MONITOR_PROPS.union({"disables"})

    for monitor_pattern, rules in value.items():
        if not isinstance(rules, dict):
            continue
        for key, val in rules.items():
            # Skip known static properties (validated by children schema)
            if key in known_props:
                continue
            # Check if it's a valid placement direction
            key_lower = key.lower().replace("_", "")
            if not any(key_lower.startswith(d) for d in PLACEMENT_DIRECTIONS):
                errors.append(f"Invalid placement rule '{key}' for '{monitor_pattern}'")
            # Validate placement target value type
            elif not isinstance(val, str) and not (isinstance(val, list) and all(isinstance(o, str) for o in val)):
                errors.append(f"Invalid placement value for '{monitor_pattern}.{key}': expected string or list of strings")

    return errors
