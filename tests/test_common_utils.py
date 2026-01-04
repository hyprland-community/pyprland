import pytest
from pyprland.common import merge, apply_filter, is_rotated, prepare_for_quotes


def test_merge_dicts():
    d1 = {"a": 1, "b": {"x": 10}}
    d2 = {"b": {"y": 20}, "c": 3}
    expected = {"a": 1, "b": {"x": 10, "y": 20}, "c": 3}
    assert merge(d1, d2) == expected


def test_merge_lists():
    d1 = {"a": [1, 2]}
    d2 = {"a": [3, 4]}
    expected = {"a": [1, 2, 3, 4]}
    assert merge(d1, d2) == expected


def test_merge_overwrite():
    d1 = {"a": 1}
    d2 = {"a": 2}
    expected = {"a": 2}
    assert merge(d1, d2) == expected


def test_apply_filter_empty():
    assert apply_filter("hello", "") == "hello"


def test_apply_filter_substitute():
    assert apply_filter("hello world", "s/world/there/") == "hello there"
    assert apply_filter("hello world", "s|world|there|") == "hello there"


def test_apply_filter_substitute_global():
    assert apply_filter("foo bar foo", "s/foo/baz/g") == "baz bar baz"
    assert apply_filter("foo bar foo", "s/foo/baz/") == "baz bar foo"


def test_apply_filter_malformed():
    # Should not crash
    assert apply_filter("hello", "s/incomplete") == "hello"
    assert apply_filter("hello", "invalid") == "hello"


def test_is_rotated():
    assert is_rotated({"transform": 1}) is True
    assert is_rotated({"transform": 3}) is True
    assert is_rotated({"transform": 5}) is True
    assert is_rotated({"transform": 7}) is True

    assert is_rotated({"transform": 0}) is False
    assert is_rotated({"transform": 2}) is False
    assert is_rotated({"transform": 4}) is False
    assert is_rotated({"transform": 6}) is False


def test_prepare_for_quotes():
    assert prepare_for_quotes('hello "world"') == 'hello \\"world\\"'
