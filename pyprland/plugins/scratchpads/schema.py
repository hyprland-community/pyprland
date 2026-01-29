"""Configuration schema for scratchpads plugin."""

import logging

from pyprland.validation import ConfigField, ConfigItems, ConfigValidator

# Null logger for validation (warnings become part of error list)
_null_logger = logging.getLogger("scratchpads.schema")
_null_logger.addHandler(logging.NullHandler())


def _validate_against_schema(config: dict, prefix: str, schema: ConfigItems) -> list[str]:
    """Validate config against schema and return errors.

    Args:
        config: Configuration dictionary to validate
        prefix: Error message prefix (e.g., "scratchpads.myterm")
        schema: Schema to validate against

    Returns:
        List of error messages (empty if valid)
    """
    validator = ConfigValidator(config, prefix, _null_logger)
    errors = validator.validate(schema)
    errors.extend(validator.warn_unknown_keys(schema))
    return errors


def _validate_animation(value: str) -> list[str]:
    """Case-insensitive animation validation."""
    valid = {"", "fromtop", "frombottom", "fromleft", "fromright"}
    if not isinstance(value, str) or value.lower() not in valid:
        return [f"invalid value '{value}' -> Valid: '', 'fromTop', 'fromBottom', 'fromLeft', 'fromRight'"]
    return []


# Schema for individual scratchpad configuration
SCRATCHPAD_SCHEMA = ConfigItems(
    # Required
    ConfigField("command", str, required=True, description="Command to run (omit for unmanaged scratchpads)"),
    # Basic
    ConfigField("class", str, default="", recommended=True, description="Window class for matching"),
    ConfigField(
        "animation",
        str,
        default="fromTop",
        description="Animation type",
        choices=["", "fromTop", "fromBottom", "fromLeft", "fromRight"],
        validator=_validate_animation,
    ),
    ConfigField("size", str, default="80% 80%", recommended=True, description="Window size (e.g. '80% 80%')"),
    # Positioning
    ConfigField("position", str, default="", description="Explicit position override"),
    ConfigField("margin", int, default=60, description="Pixels from screen edge"),
    ConfigField("offset", str, default="100%", description="Hide animation distance"),
    ConfigField("max_size", str, default="", description="Maximum window size"),
    # Behavior
    ConfigField("lazy", bool, default=True, description="Start on first use"),
    ConfigField("pinned", bool, default=True, description="Sticky to monitor"),
    ConfigField("multi", bool, default=True, description="Allow multiple windows"),
    ConfigField("unfocus", str, default="", description="Action on unfocus ('hide' or empty)"),
    ConfigField("hysteresis", float, default=0.4, description="Delay before unfocus hide"),
    ConfigField("excludes", list, default=[], description="Scratches to hide when shown"),
    ConfigField("restore_excluded", bool, default=False, description="Restore excluded on hide"),
    ConfigField("preserve_aspect", bool, default=False, description="Keep size/position across shows"),
    ConfigField("hide_delay", float, default=0.0, description="Delay before hide animation"),
    ConfigField("force_monitor", str, default="", description="Always show on specific monitor"),
    ConfigField("alt_toggle", bool, default=False, description="Alternative toggle for multi-monitor"),
    ConfigField(
        "allow_special_workspaces",
        bool,
        default=True,
        description="Allow over special workspaces",
    ),
    ConfigField("smart_focus", bool, default=True, description="Restore focus on hide"),
    ConfigField("close_on_hide", bool, default=False, description="Close instead of hide"),
    # Non-standard/troubleshooting
    ConfigField(
        "match_by",
        str,
        default="pid",
        description="Match method: pid, class, initialClass, title, initialTitle",
    ),
    ConfigField(
        "initialClass",
        str,
        default="",
        description="Match value when match_by='initialClass'",
    ),
    ConfigField(
        "initialTitle",
        str,
        default="",
        description="Match value when match_by='initialTitle'",
    ),
    ConfigField("title", str, default="", description="Match value when match_by='title'"),
    ConfigField("process_tracking", bool, default=True, description="Enable process management"),
    ConfigField(
        "skip_windowrules",
        list,
        default=[],
        description="Rules to skip: aspect, float, workspace",
    ),
    # Template/inheritance
    ConfigField("use", str, default="", description="Inherit from another scratchpad definition"),
    ConfigField("monitor", dict, default={}, description="Per-monitor config overrides"),
)

# Schema for monitor overrides (excludes non-overridable fields)
_MONITOR_OVERRIDE_SCHEMA = ConfigItems(*(f for f in SCRATCHPAD_SCHEMA if f.name not in {"command", "use", "monitor"}))


def _validate_monitor_overrides(name: str, scratch_config: dict, errors: list[str]) -> None:
    """Validate monitor sub-subsections (per-monitor overrides)."""
    monitor_overrides = scratch_config.get("monitor")
    if not monitor_overrides or not isinstance(monitor_overrides, dict):
        return

    for monitor_name, override_config in monitor_overrides.items():
        prefix = f"scratchpads.{name}.monitor.{monitor_name}"
        if not isinstance(override_config, dict):
            errors.append(f"[{prefix}] expected dict, got {type(override_config).__name__}")
            continue

        errors.extend(_validate_against_schema(override_config, prefix, _MONITOR_OVERRIDE_SCHEMA))


def validate_scratchpad_config(name: str, scratch_config: dict) -> list[str]:
    """Validate a single scratchpad's configuration.

    Args:
        name: The scratchpad name (for error messages)
        scratch_config: The scratchpad's config dict

    Returns:
        List of error messages (empty if valid)
    """
    errors: list[str] = []
    prefix = f"scratchpads.{name}"

    # Standard schema validation via ConfigValidator
    errors.extend(_validate_against_schema(scratch_config, prefix, SCRATCHPAD_SCHEMA))

    # Cross-field validations (scratchpad-specific)
    # Note: Using inline default because we're validating raw user config before schema is applied
    match_by = scratch_config.get("match_by", "pid")
    if match_by != "pid" and match_by not in scratch_config:
        errors.append(f"[{prefix}] match_by='{match_by}' requires '{match_by}' to be defined")

    # Validate unmanaged scratchpads (no command) require class for matching
    if not scratch_config.get("command") and not scratch_config.get("class"):
        errors.append(f"[{prefix}] unmanaged scratchpads (no command) require 'class' to be defined")

    _validate_monitor_overrides(name, scratch_config, errors)

    return errors
