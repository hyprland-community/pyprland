from pyprland.config import Configuration
from pyprland.validation import ConfigField, ConfigValidator, _find_similar_key, format_config_error


def test_config_access(test_logger):
    conf = Configuration({"a": 1, "b": "test"}, logger=test_logger)
    assert conf["a"] == 1
    assert conf.get("b") == "test"
    assert conf.get("c", 3) == 3


def test_get_bool(test_logger):
    conf = Configuration(
        {
            "t1": True,
            "t2": "true",
            "t3": "yes",
            "t4": "on",
            "t5": "1",
            "f1": False,
            "f2": "false",
            "f3": "no",
            "f4": "off",
            "f5": "0",
            "invalid": "foo",
            "empty": "",
        },
        logger=test_logger,
    )

    assert conf.get_bool("t1") is True
    assert conf.get_bool("t2") is True
    assert conf.get_bool("t3") is True
    assert conf.get_bool("t4") is True
    assert conf.get_bool("t5") is True

    assert conf.get_bool("f1") is False
    assert conf.get_bool("f2") is False
    assert conf.get_bool("f3") is False
    assert conf.get_bool("f4") is False
    assert conf.get_bool("f5") is False

    # Non-empty unrecognized strings are truthy (blacklist approach)
    assert conf.get_bool("invalid") is True

    # Empty string is always falsy
    assert conf.get_bool("empty") is False

    assert conf.get_bool("missing", default=True) is True
    assert conf.get_bool("missing", default=False) is False


def test_get_int(test_logger):
    conf = Configuration({"a": 1, "b": "2", "c": "invalid"}, logger=test_logger)
    assert conf.get_int("a") == 1
    assert conf.get_int("b") == 2
    assert conf.get_int("c", default=10) == 10
    assert conf.get_int("missing", default=5) == 5


def test_get_float(test_logger):
    conf = Configuration({"a": 1.5, "b": "2.5", "c": "invalid"}, logger=test_logger)
    assert conf.get_float("a") == 1.5
    assert conf.get_float("b") == 2.5
    assert conf.get_float("c", default=10.0) == 10.0
    assert conf.get_float("missing", default=5.5) == 5.5


def test_get_str(test_logger):
    conf = Configuration({"a": "text", "b": 123}, logger=test_logger)
    assert conf.get_str("a") == "text"
    assert conf.get_str("b") == "123"
    assert conf.get_str("missing", "default") == "default"


def test_iter_subsections(test_logger):
    conf = Configuration(
        {
            "global_opt": "value",
            "debug": True,
            "scratchpad1": {"command": "cmd1"},
            "scratchpad2": {"command": "cmd2"},
            "nested": {"sub": "val"},
        },
        logger=test_logger,
    )

    subsections = dict(conf.iter_subsections())

    assert len(subsections) == 3
    assert "scratchpad1" in subsections
    assert "scratchpad2" in subsections
    assert "nested" in subsections
    assert "global_opt" not in subsections
    assert "debug" not in subsections
    assert subsections["scratchpad1"] == {"command": "cmd1"}


# Config Validation Tests


def test_config_field_defaults():
    """Test ConfigField default values."""
    field = ConfigField("test")
    assert field.name == "test"
    assert field.field_type is str
    assert field.required is False
    assert field.default is None
    assert field.description == ""
    assert field.choices is None


def test_config_field_with_values():
    """Test ConfigField with custom values."""
    field = ConfigField(
        "margin",
        int,
        required=True,
        default=60,
        description="Window margin",
        choices=[30, 60, 90],
    )
    assert field.name == "margin"
    assert field.field_type is int
    assert field.required is True
    assert field.default == 60
    assert field.description == "Window margin"
    assert field.choices == [30, 60, 90]


def test_find_similar_key():
    """Test fuzzy key matching."""
    known_keys = ["command", "class", "animation", "margin"]

    # Exact match shouldn't happen (would be found first)
    # Close typos
    assert _find_similar_key("comand", known_keys) == "command"
    assert _find_similar_key("comandd", known_keys) == "command"
    assert _find_similar_key("animaton", known_keys) == "animation"
    assert _find_similar_key("margn", known_keys) == "margin"

    # Too far - no match
    assert _find_similar_key("xyz", known_keys) is None
    assert _find_similar_key("foobar", known_keys) is None


def test_format_config_error():
    """Test error message formatting."""
    msg = format_config_error("scratchpads", "command", "Missing required field")
    assert "[scratchpads]" in msg
    assert "command" in msg
    assert "Missing required field" in msg

    msg_with_suggestion = format_config_error("scratchpads", "command", "Missing required field", 'Add command = "value"')
    assert 'Add command = "value"' in msg_with_suggestion


def test_config_validator_required_fields(test_logger):
    """Test validation of required fields."""
    schema = [
        ConfigField("command", str, required=True),
        ConfigField("class", str, required=False),
    ]

    # Missing required field
    validator = ConfigValidator({}, "test_plugin", test_logger)
    errors = validator.validate(schema)
    assert len(errors) == 1
    assert "command" in errors[0]
    assert "Missing required field" in errors[0]

    # Required field present
    validator = ConfigValidator({"command": "kitty"}, "test_plugin", test_logger)
    errors = validator.validate(schema)
    assert len(errors) == 0


def test_config_validator_type_checking(test_logger):
    """Test type validation."""
    schema = [
        ConfigField("count", int),
        ConfigField("factor", float),
        ConfigField("enabled", bool),
        ConfigField("name", str),
        ConfigField("items", list),
        ConfigField("options", dict),
    ]

    # All correct types
    config = {
        "count": 10,
        "factor": 2.5,
        "enabled": True,
        "name": "test",
        "items": [1, 2, 3],
        "options": {"a": 1},
    }
    validator = ConfigValidator(config, "test_plugin", test_logger)
    errors = validator.validate(schema)
    assert len(errors) == 0

    # Wrong types
    config_bad = {
        "count": "not a number",
        "factor": "not a float",
        "enabled": "maybe",  # Invalid bool string
        "name": 123,  # Wrong - expected str
        "items": "not a list",
        "options": "not a dict",
    }
    validator = ConfigValidator(config_bad, "test_plugin", test_logger)
    errors = validator.validate(schema)
    # All 6 fields should fail with wrong types
    assert len(errors) == 6


def test_config_validator_choices(test_logger):
    """Test validation of choice fields."""
    schema = [
        ConfigField("animation", str, choices=["fromTop", "fromBottom", "fromLeft", "fromRight"]),
    ]

    # Valid choice
    validator = ConfigValidator({"animation": "fromTop"}, "test_plugin", test_logger)
    errors = validator.validate(schema)
    assert len(errors) == 0

    # Invalid choice
    validator = ConfigValidator({"animation": "fromUp"}, "test_plugin", test_logger)
    errors = validator.validate(schema)
    assert len(errors) == 1
    assert "fromUp" in errors[0]
    assert "Valid options" in errors[0]


def test_config_validator_unknown_keys(test_logger):
    """Test warning for unknown configuration keys."""
    schema = [
        ConfigField("command", str),
        ConfigField("class", str),
    ]

    config = {
        "command": "kitty",
        "class": "kitty",
        "comandd": "typo",  # Unknown key, similar to 'command'
        "foobar": "value",  # Unknown key, no similar match
    }

    validator = ConfigValidator(config, "test_plugin", test_logger)
    warnings = validator.warn_unknown_keys(schema)

    assert len(warnings) == 2
    # Check for typo suggestion
    assert any("comandd" in w and "command" in w for w in warnings)
    # Check for unknown key without suggestion
    assert any("foobar" in w for w in warnings)


def test_config_validator_numeric_strings(test_logger):
    """Test that numeric strings are accepted for int/float fields."""
    schema = [
        ConfigField("count", int),
        ConfigField("factor", float),
    ]

    # String numbers should be accepted
    config = {"count": "42", "factor": "2.5"}
    validator = ConfigValidator(config, "test_plugin", test_logger)
    errors = validator.validate(schema)
    assert len(errors) == 0


def test_config_validator_optional_fields(test_logger):
    """Test that optional fields don't trigger errors when missing."""
    schema = [
        ConfigField("optional1", str),
        ConfigField("optional2", int, default=10),
    ]

    # Empty config should be valid
    validator = ConfigValidator({}, "test_plugin", test_logger)
    errors = validator.validate(schema)
    assert len(errors) == 0


def test_config_validator_union_types(test_logger):
    """Test validation of fields that accept multiple types (union types)."""
    schema = [
        ConfigField("path", (str, list), required=True, description="Path or list of paths"),
        ConfigField("setting", (int, str), description="Can be int or string"),
    ]

    # String value for path should work
    validator = ConfigValidator({"path": "/some/path"}, "test_plugin", test_logger)
    errors = validator.validate(schema)
    assert len(errors) == 0

    # List value for path should work
    validator = ConfigValidator({"path": ["/path1", "/path2"]}, "test_plugin", test_logger)
    errors = validator.validate(schema)
    assert len(errors) == 0

    # Int value for setting should work
    validator = ConfigValidator({"path": "/some/path", "setting": 42}, "test_plugin", test_logger)
    errors = validator.validate(schema)
    assert len(errors) == 0

    # String value for setting should work
    validator = ConfigValidator({"path": "/some/path", "setting": "auto"}, "test_plugin", test_logger)
    errors = validator.validate(schema)
    assert len(errors) == 0

    # Wrong type for path (dict) should fail
    validator = ConfigValidator({"path": {"key": "value"}}, "test_plugin", test_logger)
    errors = validator.validate(schema)
    assert len(errors) == 1
    assert "str or list" in errors[0]

    # Wrong type for setting (list) should fail
    validator = ConfigValidator({"path": "/some/path", "setting": [1, 2, 3]}, "test_plugin", test_logger)
    errors = validator.validate(schema)
    assert len(errors) == 1
    assert "int or str" in errors[0]
