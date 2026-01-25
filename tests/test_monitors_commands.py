"""Unit tests for pyprland.plugins.monitors.commands module."""

import pytest

from pyprland.plugins.monitors.commands import (
    NIRI_TRANSFORM_NAMES,
    build_hyprland_command,
    build_niri_disable_action,
    build_niri_position_action,
    build_niri_scale_action,
    build_niri_transform_action,
)


class TestBuildHyprlandCommand:
    """Tests for build_hyprland_command function."""

    def test_basic_command(self):
        """Test basic command generation with defaults from monitor."""
        monitor = {
            "name": "DP-1",
            "width": 1920,
            "height": 1080,
            "refreshRate": 60,
            "scale": 1.0,
            "x": 0,
            "y": 0,
            "transform": 0,
        }
        config = {}

        result = build_hyprland_command(monitor, config)

        assert result == "monitor DP-1,1920x1080@60,0x0,1.0,transform,0"

    def test_with_custom_resolution_string(self):
        """Test with custom resolution as string."""
        monitor = {
            "name": "HDMI-A-1",
            "width": 1920,
            "height": 1080,
            "refreshRate": 60,
            "scale": 1.0,
            "x": 100,
            "y": 200,
            "transform": 0,
        }
        config = {"resolution": "2560x1440"}

        result = build_hyprland_command(monitor, config)

        assert result == "monitor HDMI-A-1,2560x1440@60,100x200,1.0,transform,0"

    def test_with_custom_resolution_list(self):
        """Test with custom resolution as list."""
        monitor = {
            "name": "DP-2",
            "width": 1920,
            "height": 1080,
            "refreshRate": 60,
            "scale": 1.0,
            "x": 0,
            "y": 0,
            "transform": 0,
        }
        config = {"resolution": [3840, 2160]}

        result = build_hyprland_command(monitor, config)

        assert result == "monitor DP-2,3840x2160@60,0x0,1.0,transform,0"

    def test_with_custom_scale(self):
        """Test with custom scale."""
        monitor = {
            "name": "DP-1",
            "width": 3840,
            "height": 2160,
            "refreshRate": 60,
            "scale": 1.0,
            "x": 0,
            "y": 0,
            "transform": 0,
        }
        config = {"scale": 2.0}

        result = build_hyprland_command(monitor, config)

        assert result == "monitor DP-1,3840x2160@60,0x0,2.0,transform,0"

    def test_with_custom_rate(self):
        """Test with custom refresh rate."""
        monitor = {
            "name": "DP-1",
            "width": 1920,
            "height": 1080,
            "refreshRate": 60,
            "scale": 1.0,
            "x": 0,
            "y": 0,
            "transform": 0,
        }
        config = {"rate": 144}

        result = build_hyprland_command(monitor, config)

        assert result == "monitor DP-1,1920x1080@144,0x0,1.0,transform,0"

    def test_with_transform(self):
        """Test with transform."""
        monitor = {
            "name": "DP-1",
            "width": 1920,
            "height": 1080,
            "refreshRate": 60,
            "scale": 1.0,
            "x": 0,
            "y": 0,
            "transform": 0,
        }
        config = {"transform": 1}

        result = build_hyprland_command(monitor, config)

        assert result == "monitor DP-1,1920x1080@60,0x0,1.0,transform,1"


class TestBuildNiriPositionAction:
    """Tests for build_niri_position_action function."""

    def test_basic_position(self):
        """Test basic position action."""
        result = build_niri_position_action("DP-1", 100, 200)

        assert result == {
            "Output": {
                "output": "DP-1",
                "action": {"Position": {"Specific": {"x": 100, "y": 200}}},
            }
        }

    def test_zero_position(self):
        """Test zero position."""
        result = build_niri_position_action("HDMI-A-1", 0, 0)

        assert result["Output"]["action"]["Position"]["Specific"]["x"] == 0
        assert result["Output"]["action"]["Position"]["Specific"]["y"] == 0


class TestBuildNiriScaleAction:
    """Tests for build_niri_scale_action function."""

    def test_scale_1(self):
        """Test scale of 1."""
        result = build_niri_scale_action("DP-1", 1.0)

        assert result == {"Output": {"output": "DP-1", "action": {"Scale": {"Specific": 1.0}}}}

    def test_scale_2(self):
        """Test scale of 2."""
        result = build_niri_scale_action("DP-1", 2.0)

        assert result["Output"]["action"]["Scale"]["Specific"] == 2.0

    def test_scale_fractional(self):
        """Test fractional scale."""
        result = build_niri_scale_action("DP-1", 1.5)

        assert result["Output"]["action"]["Scale"]["Specific"] == 1.5


class TestBuildNiriTransformAction:
    """Tests for build_niri_transform_action function."""

    def test_transform_0(self):
        """Test transform 0 (Normal)."""
        result = build_niri_transform_action("DP-1", 0)

        assert result == {
            "Output": {
                "output": "DP-1",
                "action": {"Transform": {"transform": "Normal"}},
            }
        }

    def test_transform_1(self):
        """Test transform 1 (90 degrees)."""
        result = build_niri_transform_action("DP-1", 1)

        assert result["Output"]["action"]["Transform"]["transform"] == "90"

    def test_transform_4(self):
        """Test transform 4 (Flipped)."""
        result = build_niri_transform_action("DP-1", 4)

        assert result["Output"]["action"]["Transform"]["transform"] == "Flipped"

    def test_transform_string(self):
        """Test transform as string (passthrough)."""
        result = build_niri_transform_action("DP-1", "Flipped90")

        assert result["Output"]["action"]["Transform"]["transform"] == "Flipped90"

    def test_transform_out_of_range(self):
        """Test transform out of range uses string."""
        result = build_niri_transform_action("DP-1", 99)

        assert result["Output"]["action"]["Transform"]["transform"] == "99"


class TestBuildNiriDisableAction:
    """Tests for build_niri_disable_action function."""

    def test_disable(self):
        """Test disable action."""
        result = build_niri_disable_action("DP-1")

        assert result == {"Output": {"output": "DP-1", "action": "Off"}}


class TestNiriTransformNames:
    """Tests for NIRI_TRANSFORM_NAMES constant."""

    def test_length(self):
        """Test there are 8 transform names."""
        assert len(NIRI_TRANSFORM_NAMES) == 8

    def test_values(self):
        """Test transform names values."""
        assert NIRI_TRANSFORM_NAMES[0] == "Normal"
        assert NIRI_TRANSFORM_NAMES[1] == "90"
        assert NIRI_TRANSFORM_NAMES[2] == "180"
        assert NIRI_TRANSFORM_NAMES[3] == "270"
        assert NIRI_TRANSFORM_NAMES[4] == "Flipped"
