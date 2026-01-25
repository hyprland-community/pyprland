"""Tests for the ansi module."""

import os
from io import StringIO
from unittest.mock import patch

from pyprland.ansi import (
    BOLD,
    DIM,
    RED,
    RESET,
    YELLOW,
    HandlerStyles,
    LogStyles,
    colorize,
    make_style,
    should_colorize,
)


def test_colorize_single_code():
    """Test colorize with a single ANSI code."""
    result = colorize("hello", RED)
    assert result == "\x1b[31mhello\x1b[0m"


def test_colorize_multiple_codes():
    """Test colorize with multiple ANSI codes."""
    result = colorize("hello", RED, BOLD)
    assert result == "\x1b[31;1mhello\x1b[0m"


def test_colorize_no_codes():
    """Test colorize with no codes returns text unchanged."""
    result = colorize("hello")
    assert result == "hello"


def test_make_style():
    """Test make_style returns correct prefix and suffix."""
    prefix, suffix = make_style(YELLOW, DIM)
    assert prefix == "\x1b[33;2m"
    assert suffix == RESET


def test_make_style_no_codes():
    """Test make_style with no codes returns empty prefix."""
    prefix, suffix = make_style()
    assert prefix == ""
    assert suffix == RESET


def test_should_colorize_respects_no_color():
    """Test that NO_COLOR environment variable disables colors."""
    with patch.dict(os.environ, {"NO_COLOR": "1"}, clear=False):
        assert should_colorize() is False


def test_should_colorize_respects_force_color():
    """Test that FORCE_COLOR environment variable forces colors."""
    # Create a non-TTY stream
    stream = StringIO()
    with patch.dict(os.environ, {"FORCE_COLOR": "1", "NO_COLOR": ""}, clear=False):
        assert should_colorize(stream) is True


def test_should_colorize_non_tty():
    """Test that non-TTY streams don't get colors by default."""
    stream = StringIO()
    with patch.dict(os.environ, {"NO_COLOR": "", "FORCE_COLOR": ""}, clear=False):
        assert should_colorize(stream) is False


def test_log_styles():
    """Test LogStyles contains expected style tuples."""
    assert LogStyles.WARNING == (YELLOW, DIM)
    assert LogStyles.ERROR == (RED, DIM)
    assert LogStyles.CRITICAL == (RED, BOLD)


def test_handler_styles():
    """Test HandlerStyles contains expected style tuples."""
    assert HandlerStyles.COMMAND == (YELLOW, BOLD)
    assert HandlerStyles.EVENT == ("30", BOLD)  # BLACK = "30"


def test_constants():
    """Test that ANSI constants have expected values."""
    assert RESET == "\x1b[0m"
    assert BOLD == "1"
    assert DIM == "2"
    assert RED == "31"
    assert YELLOW == "33"
