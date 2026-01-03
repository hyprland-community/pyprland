import pytest
from unittest.mock import Mock
from pyprland.common import Configuration


def test_config_access():
    conf = Configuration({"a": 1, "b": "test"})
    assert conf["a"] == 1
    assert conf.get("b") == "test"
    assert conf.get("c", 3) == 3


def test_get_bool():
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
        }
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

    assert conf.get_bool("missing", default=True) is True
    assert conf.get_bool("missing", default=False) is False


def test_get_int():
    conf = Configuration({"a": 1, "b": "2", "c": "invalid"})
    assert conf.get_int("a") == 1
    assert conf.get_int("b") == 2
    assert conf.get_int("c", default=10) == 10
    assert conf.get_int("missing", default=5) == 5


def test_get_str():
    conf = Configuration({"a": "text", "b": 123})
    assert conf.get_str("a") == "text"
    assert conf.get_str("b") == "123"
    assert conf.get_str("missing", "default") == "default"


def test_iter_subsections():
    conf = Configuration(
        {
            "global_opt": "value",
            "debug": True,
            "scratchpad1": {"command": "cmd1"},
            "scratchpad2": {"command": "cmd2"},
            "nested": {"sub": "val"},
        }
    )

    subsections = dict(conf.iter_subsections())

    assert len(subsections) == 3
    assert "scratchpad1" in subsections
    assert "scratchpad2" in subsections
    assert "nested" in subsections
    assert "global_opt" not in subsections
    assert "debug" not in subsections
    assert subsections["scratchpad1"] == {"command": "cmd1"}
