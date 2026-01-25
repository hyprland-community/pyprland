"""Tests for fallback adapters (wayland, xorg)."""

import logging
import pytest
from pyprland.adapters.wayland import WaylandBackend
from pyprland.adapters.xorg import XorgBackend
from pyprland.common import SharedState


@pytest.fixture
def test_log():
    """Provide a silent logger for tests."""
    logger = logging.getLogger("test_adapters")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


@pytest.fixture
def mock_state():
    """Provide a mock SharedState for tests."""
    return SharedState()


class TestWaylandBackend:
    """Tests for WaylandBackend wlr-randr parsing."""

    def test_parse_single_monitor(self, test_log, mock_state):
        """Test parsing a single monitor output."""
        output = """DP-1 "Dell Inc. DELL U2415 ABC123"
  Enabled: yes
  Modes:
    1920x1200 px, 59.950 Hz (preferred, current)
    1920x1080 px, 60.000 Hz
  Position: 0,0
  Transform: normal
  Scale: 1.000000
"""
        backend = WaylandBackend(mock_state)
        monitors = backend._parse_wlr_randr_output(output, False, test_log)

        assert len(monitors) == 1
        assert monitors[0]["name"] == "DP-1"
        assert monitors[0]["width"] == 1920
        assert monitors[0]["height"] == 1200
        assert monitors[0]["x"] == 0
        assert monitors[0]["y"] == 0
        assert monitors[0]["scale"] == 1.0
        assert monitors[0]["transform"] == 0
        assert monitors[0]["refreshRate"] == 59.95

    def test_parse_multiple_monitors(self, test_log, mock_state):
        """Test parsing multiple monitors."""
        output = """DP-1 "Primary Monitor"
  Enabled: yes
  Modes:
    1920x1080 px, 60.000 Hz (preferred, current)
  Position: 0,0
  Transform: normal
  Scale: 1.000000

HDMI-A-1 "Secondary Monitor"
  Enabled: yes
  Modes:
    2560x1440 px, 75.000 Hz (preferred, current)
  Position: 1920,0
  Transform: normal
  Scale: 1.500000
"""
        backend = WaylandBackend(mock_state)
        monitors = backend._parse_wlr_randr_output(output, False, test_log)

        assert len(monitors) == 2
        assert monitors[0]["name"] == "DP-1"
        assert monitors[0]["x"] == 0
        assert monitors[1]["name"] == "HDMI-A-1"
        assert monitors[1]["x"] == 1920
        assert monitors[1]["scale"] == 1.5
        assert monitors[1]["refreshRate"] == 75.0

    def test_parse_rotated_monitor(self, test_log, mock_state):
        """Test parsing a rotated monitor."""
        output = """eDP-1 "Laptop Display"
  Enabled: yes
  Modes:
    1920x1080 px, 60.000 Hz (preferred, current)
  Position: 0,0
  Transform: 90
  Scale: 1.000000
"""
        backend = WaylandBackend(mock_state)
        monitors = backend._parse_wlr_randr_output(output, False, test_log)

        assert len(monitors) == 1
        assert monitors[0]["transform"] == 1  # 90 degrees

    def test_parse_disabled_monitor_excluded(self, test_log, mock_state):
        """Test that disabled monitors are excluded by default."""
        output = """DP-1 "Primary"
  Enabled: yes
  Modes:
    1920x1080 px, 60.000 Hz (current)
  Position: 0,0
  Transform: normal
  Scale: 1.000000

DP-2 "Disabled"
  Enabled: no
  Modes:
    1920x1080 px, 60.000 Hz (current)
  Position: 0,0
  Transform: normal
  Scale: 1.000000
"""
        backend = WaylandBackend(mock_state)
        monitors = backend._parse_wlr_randr_output(output, False, test_log)

        assert len(monitors) == 1
        assert monitors[0]["name"] == "DP-1"

    def test_parse_disabled_monitor_included(self, test_log, mock_state):
        """Test that disabled monitors are included when requested."""
        output = """DP-1 "Primary"
  Enabled: yes
  Modes:
    1920x1080 px, 60.000 Hz (current)
  Position: 0,0
  Transform: normal
  Scale: 1.000000

DP-2 "Disabled"
  Enabled: no
  Modes:
    1920x1080 px, 60.000 Hz (current)
  Position: 0,0
  Transform: normal
  Scale: 1.000000
"""
        backend = WaylandBackend(mock_state)
        monitors = backend._parse_wlr_randr_output(output, True, test_log)

        assert len(monitors) == 2

    def test_parse_no_mode_skipped(self, test_log, mock_state):
        """Test that outputs without a current mode are skipped."""
        output = """DP-1 "No Mode"
  Enabled: yes
  Modes:
    1920x1080 px, 60.000 Hz (preferred)
  Position: 0,0
  Transform: normal
  Scale: 1.000000
"""
        backend = WaylandBackend(mock_state)
        monitors = backend._parse_wlr_randr_output(output, False, test_log)

        # No "(current)" mode, should be skipped
        assert len(monitors) == 0

    def test_parse_empty_output(self, test_log, mock_state):
        """Test parsing empty output."""
        backend = WaylandBackend(mock_state)
        monitors = backend._parse_wlr_randr_output("", False, test_log)

        assert len(monitors) == 0


class TestXorgBackend:
    """Tests for XorgBackend xrandr parsing."""

    def test_parse_single_monitor(self, test_log, mock_state):
        """Test parsing a single monitor output."""
        output = """Screen 0: minimum 8 x 8, current 1920 x 1080, maximum 32767 x 32767
DP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 527mm x 296mm
   1920x1080     60.00*+
   1680x1050     59.95
"""
        backend = XorgBackend(mock_state)
        monitors = backend._parse_xrandr_output(output, False, test_log)

        assert len(monitors) == 1
        assert monitors[0]["name"] == "DP-1"
        assert monitors[0]["width"] == 1920
        assert monitors[0]["height"] == 1080
        assert monitors[0]["x"] == 0
        assert monitors[0]["y"] == 0
        assert monitors[0]["transform"] == 0

    def test_parse_multiple_monitors(self, test_log, mock_state):
        """Test parsing multiple monitors with offsets."""
        output = """Screen 0: minimum 8 x 8, current 4480 x 1440, maximum 32767 x 32767
DP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 527mm x 296mm
   1920x1080     60.00*+
HDMI-1 connected 2560x1440+1920+0 (normal left inverted right x axis y axis) 597mm x 336mm
   2560x1440     59.95*+
"""
        backend = XorgBackend(mock_state)
        monitors = backend._parse_xrandr_output(output, False, test_log)

        assert len(monitors) == 2
        assert monitors[0]["name"] == "DP-1"
        assert monitors[0]["x"] == 0
        assert monitors[1]["name"] == "HDMI-1"
        assert monitors[1]["width"] == 2560
        assert monitors[1]["height"] == 1440
        assert monitors[1]["x"] == 1920

    def test_parse_rotated_monitor(self, test_log, mock_state):
        """Test parsing a rotated (left) monitor."""
        output = """Screen 0: minimum 8 x 8, current 1080 x 1920, maximum 32767 x 32767
DP-1 connected primary 1920x1080+0+0 left (normal left inverted right x axis y axis) 296mm x 527mm
   1920x1080     60.00*+
"""
        backend = XorgBackend(mock_state)
        monitors = backend._parse_xrandr_output(output, False, test_log)

        assert len(monitors) == 1
        assert monitors[0]["transform"] == 1  # left = 90 degrees

    def test_parse_inverted_monitor(self, test_log, mock_state):
        """Test parsing an inverted (180 deg) monitor."""
        output = """Screen 0: minimum 8 x 8, current 1920 x 1080, maximum 32767 x 32767
DP-1 connected primary 1920x1080+0+0 inverted (normal left inverted right x axis y axis) 527mm x 296mm
   1920x1080     60.00*+
"""
        backend = XorgBackend(mock_state)
        monitors = backend._parse_xrandr_output(output, False, test_log)

        assert len(monitors) == 1
        assert monitors[0]["transform"] == 2  # inverted = 180 degrees

    def test_parse_disconnected_excluded(self, test_log, mock_state):
        """Test that disconnected monitors are excluded by default."""
        output = """Screen 0: minimum 8 x 8, current 1920 x 1080, maximum 32767 x 32767
DP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 527mm x 296mm
   1920x1080     60.00*+
VGA-1 disconnected (normal left inverted right x axis y axis)
"""
        backend = XorgBackend(mock_state)
        monitors = backend._parse_xrandr_output(output, False, test_log)

        assert len(monitors) == 1
        assert monitors[0]["name"] == "DP-1"

    def test_parse_disconnected_included(self, test_log, mock_state):
        """Test that disconnected monitors can be included."""
        output = """Screen 0: minimum 8 x 8, current 1920 x 1080, maximum 32767 x 32767
DP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 527mm x 296mm
   1920x1080     60.00*+
VGA-1 disconnected (normal left inverted right x axis y axis)
"""
        backend = XorgBackend(mock_state)
        monitors = backend._parse_xrandr_output(output, True, test_log)

        assert len(monitors) == 2
        assert monitors[1]["name"] == "VGA-1"
        assert monitors[1]["width"] == 0  # Disconnected has no resolution

    def test_parse_empty_output(self, test_log, mock_state):
        """Test parsing empty output."""
        backend = XorgBackend(mock_state)
        monitors = backend._parse_xrandr_output("", False, test_log)

        assert len(monitors) == 0

    def test_parse_connected_no_mode(self, test_log, mock_state):
        """Test that connected but inactive outputs are skipped."""
        output = """Screen 0: minimum 8 x 8, current 1920 x 1080, maximum 32767 x 32767
DP-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 527mm x 296mm
   1920x1080     60.00*+
DP-2 connected (normal left inverted right x axis y axis)
   1920x1080     60.00+
"""
        backend = XorgBackend(mock_state)
        monitors = backend._parse_xrandr_output(output, False, test_log)

        # DP-2 is connected but has no active mode (no +X+Y), should be skipped
        assert len(monitors) == 1
        assert monitors[0]["name"] == "DP-1"
