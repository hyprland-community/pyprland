"""Convert ConfigField schema to questionary questions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, get_args, get_origin

import questionary
from questionary import Choice

if TYPE_CHECKING:
    from pyprland.validation import ConfigField, ConfigItems


def _is_path_type(field_type: type | tuple) -> bool:
    """Check if field_type is Path or includes Path in a union."""
    if field_type is Path:
        return True
    if isinstance(field_type, tuple):
        return Path in field_type
    return False


def _is_path_list_type(field_type: type | tuple) -> bool:
    """Check if field_type is list[Path]."""
    origin = get_origin(field_type)
    if origin is list:
        args = get_args(field_type)
        return bool(args and args[0] is Path)
    return False


def field_to_question(field: ConfigField, current_value: Any = None) -> Any | None:  # noqa: C901
    """Convert a ConfigField to a questionary question and ask it.

    Args:
        field: The ConfigField to convert
        current_value: Current value if editing existing config

    Returns:
        The user's answer, or None if skipped/cancelled
    """
    default = current_value if current_value is not None else field.default

    # Build the question text
    question_text = field.description or f"Enter {field.name}"
    if field.required:
        question_text = f"* {question_text}"
    elif field.recommended:
        question_text = f"[Recommended] {question_text}"

    # Dispatch based on field type
    result: Any | None = None

    if field.choices:
        result = _ask_choice(question_text, field.choices, default)
    elif field.field_type is bool:
        result = _ask_bool(question_text, default)
    elif field.field_type is int:
        result = _ask_int(question_text, default)
    elif field.field_type is float:
        result = _ask_float(question_text, default)
    elif _is_path_list_type(field.field_type):
        result = _ask_path_list(question_text, default, only_directories=field.is_directory)
    elif _is_path_type(field.field_type):
        result = _ask_path(question_text, default, only_directories=field.is_directory)
    elif field.field_type is list:
        result = _ask_list(question_text, default)
    elif not (field.field_type is dict and field.children):
        # Default to text input for str and other types
        # (dict with children is skipped - handled elsewhere)
        result = _ask_text(question_text, default)

    return result


def _ask_choice(question: str, choices: list, default: Any) -> Any | None:
    """Ask user to select from choices."""
    # Build choice objects
    q_choices = [Choice(title=str(c), value=c, checked=c == default) for c in choices]

    return questionary.select(
        question,
        choices=q_choices,
        default=default,
    ).ask()


def _ask_bool(question: str, default: Any) -> bool | None:
    """Ask yes/no question."""
    default_bool = bool(default) if default is not None else False
    result = questionary.confirm(question, default=default_bool).ask()
    if result is None:
        return None
    return bool(result)


def _ask_int(question: str, default: Any) -> int | None:
    """Ask for integer input."""
    default_str = str(default) if default is not None else ""

    while True:
        result = questionary.text(
            question,
            default=default_str,
        ).ask()

        if result is None:  # Cancelled
            return None

        if result == "":  # Empty = skip
            return None

        try:
            return int(result)
        except ValueError:
            questionary.print("Please enter a valid integer.", style="fg:red")


def _ask_float(question: str, default: Any) -> float | None:
    """Ask for float input."""
    default_str = str(default) if default is not None else ""

    while True:
        result = questionary.text(
            question,
            default=default_str,
        ).ask()

        if result is None:  # Cancelled
            return None

        if result == "":  # Empty = skip
            return None

        try:
            return float(result)
        except ValueError:
            questionary.print("Please enter a valid number.", style="fg:red")


def _ask_text(question: str, default: Any) -> str | None:
    """Ask for text input."""
    default_str = str(default) if default is not None else ""
    result = questionary.text(question, default=default_str).ask()
    return result or None


def _ask_list(question: str, default: Any) -> list | None:
    """Ask for list input (comma-separated)."""
    default_str = ", ".join(str(x) for x in default) if isinstance(default, list) else str(default) if default else ""

    result = questionary.text(
        f"{question} (comma-separated)",
        default=default_str,
    ).ask()

    if result is None:  # Cancelled
        return None

    if result == "":  # Empty = empty list or skip
        return []

    # Parse comma-separated values
    return [item.strip() for item in result.split(",") if item.strip()]


def _ask_path(question: str, default: Any, only_directories: bool = False) -> str | None:
    """Ask for a single path with filesystem autocompletion."""
    default_str = str(default) if default is not None else ""
    result = questionary.path(
        question,
        default=default_str,
        only_directories=only_directories,
    ).ask()
    return result or None


def _ask_path_list(question: str, default: Any, only_directories: bool = False) -> list[str] | None:
    """Ask for multiple paths one at a time with filesystem autocompletion."""
    paths: list[str] = []

    # Display the main question
    questionary.print(f"{question}:", style="bold")

    # Show existing defaults
    if isinstance(default, list) and default:
        questionary.print(f"  Current: {', '.join(str(p) for p in default)}", style="fg:gray")

    questionary.print("  (Enter paths one at a time, empty to finish)", style="fg:gray")

    count = 1
    while True:
        result = questionary.path(
            f"  Path {count}:",
            default="",
            only_directories=only_directories,
        ).ask()

        if result is None:  # Cancelled (Ctrl+C)
            return None

        if result == "":  # Empty = done
            break

        paths.append(result)
        count += 1

    # If no paths entered but had defaults, keep defaults
    if not paths and isinstance(default, list):
        return [str(p) for p in default]

    return paths or []


def ask_plugin_options(  # noqa: C901
    plugin_name: str,
    schema: ConfigItems | None,
    only_required: bool = False,
    only_recommended: bool = True,
) -> dict:
    """Ask questions for all relevant fields in a plugin schema.

    Args:
        plugin_name: Name of the plugin (for display)
        schema: The plugin's config_schema
        only_required: If True, only ask required fields
        only_recommended: If True, also ask recommended fields (not just required)

    Returns:
        Dict of field names to values
    """
    if not schema:
        return {}

    questionary.print(f"\nConfiguring {plugin_name}:", style="bold")

    result = {}

    # Group fields by category if available
    categorized: dict[str, list] = {}
    uncategorized: list = []

    for field in schema:
        if field.category:
            if field.category not in categorized:
                categorized[field.category] = []
            categorized[field.category].append(field)
        else:
            uncategorized.append(field)

    # Process uncategorized first
    for field in uncategorized:
        value = _process_field(field, only_required, only_recommended)
        if value is not None:
            result[field.name] = value

    # Process each category
    for fields in categorized.values():
        category_values = {}
        for field in fields:
            value = _process_field(field, only_required, only_recommended)
            if value is not None:
                category_values[field.name] = value

        if category_values:
            result.update(category_values)

    return result


def _process_field(
    field: ConfigField,
    only_required: bool,
    only_recommended: bool,
) -> Any | None:
    """Process a single field and return its value if applicable."""
    # Determine if we should ask this field
    if only_required and not field.required:
        return None

    # Ask required and recommended fields (when only_recommended is True)
    if not only_required and only_recommended and not field.required and not field.recommended:
        return None

    # Skip complex dict fields for now (nested configs)
    if field.field_type is dict and field.children:
        return None

    return field_to_question(field)
