"""Unit tests for pyprland.plugins.monitors.layout module."""

import pytest

from pyprland.plugins.monitors.layout import (
    MAX_CYCLE_PATH_LENGTH,
    MONITOR_PROPS,
    build_graph,
    compute_positions,
    compute_xy,
    find_cycle_path,
    get_dims,
)


def make_monitor(name, width=1920, height=1080, x=0, y=0, scale=1.0, transform=0):
    """Helper to create a monitor dict."""
    return {
        "name": name,
        "description": f"{name} Monitor Description",
        "width": width,
        "height": height,
        "x": x,
        "y": y,
        "scale": scale,
        "transform": transform,
        "refreshRate": 60,
    }


class TestGetDims:
    """Tests for get_dims function."""

    def test_basic_dimensions(self):
        """Test basic dimensions without config."""
        monitor = make_monitor("DP-1", width=1920, height=1080)

        width, height = get_dims(monitor)

        assert width == 1920
        assert height == 1080

    def test_with_scale(self):
        """Test dimensions with scale applied."""
        monitor = make_monitor("DP-1", width=3840, height=2160, scale=2.0)

        width, height = get_dims(monitor)

        assert width == 1920
        assert height == 1080

    def test_with_config_scale(self):
        """Test dimensions with config scale override."""
        monitor = make_monitor("DP-1", width=3840, height=2160, scale=1.0)
        config = {"scale": 2.0}

        width, height = get_dims(monitor, config)

        assert width == 1920
        assert height == 1080

    def test_with_config_resolution_string(self):
        """Test dimensions with config resolution as string."""
        monitor = make_monitor("DP-1", width=1920, height=1080)
        config = {"resolution": "2560x1440"}

        width, height = get_dims(monitor, config)

        assert width == 2560
        assert height == 1440

    def test_with_config_resolution_list(self):
        """Test dimensions with config resolution as list."""
        monitor = make_monitor("DP-1", width=1920, height=1080)
        config = {"resolution": [2560, 1440]}

        width, height = get_dims(monitor, config)

        assert width == 2560
        assert height == 1440

    def test_with_transform_90(self):
        """Test dimensions with 90 degree transform (swaps width/height)."""
        monitor = make_monitor("DP-1", width=1920, height=1080, transform=1)

        width, height = get_dims(monitor)

        assert width == 1080
        assert height == 1920

    def test_with_transform_270(self):
        """Test dimensions with 270 degree transform (swaps width/height)."""
        monitor = make_monitor("DP-1", width=1920, height=1080, transform=3)

        width, height = get_dims(monitor)

        assert width == 1080
        assert height == 1920

    def test_with_transform_180(self):
        """Test dimensions with 180 degree transform (no swap)."""
        monitor = make_monitor("DP-1", width=1920, height=1080, transform=2)

        width, height = get_dims(monitor)

        assert width == 1920
        assert height == 1080


class TestComputeXy:
    """Tests for compute_xy function."""

    def test_left(self):
        """Test left placement."""
        ref_rect = (100, 100, 1920, 1080)  # x, y, width, height
        mon_dim = (1920, 1080)  # width, height

        x, y = compute_xy(ref_rect, mon_dim, "left")

        assert x == -1820  # 100 - 1920
        assert y == 100

    def test_right(self):
        """Test right placement."""
        ref_rect = (0, 0, 1920, 1080)
        mon_dim = (1920, 1080)

        x, y = compute_xy(ref_rect, mon_dim, "right")

        assert x == 1920
        assert y == 0

    def test_top(self):
        """Test top placement."""
        ref_rect = (0, 1080, 1920, 1080)
        mon_dim = (1920, 1080)

        x, y = compute_xy(ref_rect, mon_dim, "top")

        assert x == 0
        assert y == 0

    def test_bottom(self):
        """Test bottom placement."""
        ref_rect = (0, 0, 1920, 1080)
        mon_dim = (1920, 1080)

        x, y = compute_xy(ref_rect, mon_dim, "bottom")

        assert x == 0
        assert y == 1080

    def test_left_center(self):
        """Test left-center placement."""
        ref_rect = (0, 0, 1920, 1080)
        mon_dim = (1920, 500)

        x, y = compute_xy(ref_rect, mon_dim, "left-center")

        assert x == -1920
        assert y == 290  # (1080 - 500) // 2

    def test_right_center(self):
        """Test right-center placement."""
        ref_rect = (0, 0, 1920, 1080)
        mon_dim = (1920, 500)

        x, y = compute_xy(ref_rect, mon_dim, "rightCenter")

        assert x == 1920
        assert y == 290

    def test_top_center(self):
        """Test top-center placement."""
        ref_rect = (0, 1080, 1920, 1080)
        mon_dim = (1000, 1080)

        x, y = compute_xy(ref_rect, mon_dim, "top_center")

        assert x == 460  # (1920 - 1000) // 2
        assert y == 0

    def test_bottom_end(self):
        """Test bottom-end placement."""
        ref_rect = (0, 0, 1920, 1080)
        mon_dim = (1000, 1080)

        x, y = compute_xy(ref_rect, mon_dim, "bottom-end")

        assert x == 920  # 1920 - 1000
        assert y == 1080

    def test_unknown_rule_returns_ref_position(self):
        """Test that unknown rule returns reference position."""
        ref_rect = (100, 200, 1920, 1080)
        mon_dim = (1920, 1080)

        x, y = compute_xy(ref_rect, mon_dim, "unknown")

        assert x == 100
        assert y == 200


class TestBuildGraph:
    """Tests for build_graph function."""

    def test_basic_graph(self):
        """Test basic graph building."""
        monitors_by_name = {
            "DP-1": make_monitor("DP-1"),
            "DP-2": make_monitor("DP-2"),
        }
        config = {
            "DP-2": {"rightOf": ["DP-1"]},
        }

        tree, in_degree, multi_target_info = build_graph(config, monitors_by_name)

        assert ("DP-2", "rightOf") in tree["DP-1"]
        assert in_degree["DP-1"] == 0
        assert in_degree["DP-2"] == 1
        assert multi_target_info == []

    def test_multiple_targets_reported(self):
        """Test that multiple targets are reported."""
        monitors_by_name = {
            "DP-1": make_monitor("DP-1"),
            "DP-2": make_monitor("DP-2"),
            "DP-3": make_monitor("DP-3"),
        }
        config = {
            "DP-2": {"rightOf": ["DP-1", "DP-3"]},
        }

        tree, in_degree, multi_target_info = build_graph(config, monitors_by_name)

        assert len(multi_target_info) == 1
        assert multi_target_info[0] == ("DP-2", "rightOf", ["DP-1", "DP-3"])
        # Should only use first target
        assert ("DP-2", "rightOf") in tree["DP-1"]
        assert ("DP-2", "rightOf") not in tree["DP-3"]

    def test_ignores_monitor_props(self):
        """Test that monitor props are ignored."""
        monitors_by_name = {
            "DP-1": make_monitor("DP-1"),
            "DP-2": make_monitor("DP-2"),
        }
        config = {
            "DP-2": {"rightOf": ["DP-1"], "scale": 2.0, "resolution": "1920x1080"},
        }

        tree, in_degree, _ = build_graph(config, monitors_by_name)

        # Only rightOf should create a dependency
        assert in_degree["DP-2"] == 1

    def test_ignores_disables(self):
        """Test that disables is ignored in graph building."""
        monitors_by_name = {
            "DP-1": make_monitor("DP-1"),
            "DP-2": make_monitor("DP-2"),
        }
        config = {
            "DP-1": {"disables": ["DP-3"]},
        }

        tree, in_degree, _ = build_graph(config, monitors_by_name)

        assert in_degree["DP-1"] == 0
        assert in_degree["DP-2"] == 0


class TestComputePositions:
    """Tests for compute_positions function."""

    def test_chain_layout(self):
        """Test a chain of monitors: DP-1 -> DP-2 -> DP-3."""
        monitors = {
            "DP-1": make_monitor("DP-1", x=0, y=0),
            "DP-2": make_monitor("DP-2", x=0, y=0),
            "DP-3": make_monitor("DP-3", x=0, y=0),
        }
        config = {
            "DP-2": {"rightOf": ["DP-1"]},
            "DP-3": {"rightOf": ["DP-2"]},
        }
        tree, in_degree, _ = build_graph(config, monitors)

        positions, unprocessed = compute_positions(monitors, tree, in_degree, config)

        assert positions["DP-1"] == (0, 0)
        assert positions["DP-2"] == (1920, 0)
        assert positions["DP-3"] == (3840, 0)
        assert unprocessed == []

    def test_circular_dependency(self):
        """Test that circular dependencies are detected."""
        monitors = {
            "DP-1": make_monitor("DP-1", x=0, y=0),
            "DP-2": make_monitor("DP-2", x=0, y=0),
        }
        config = {
            "DP-1": {"rightOf": ["DP-2"]},
            "DP-2": {"rightOf": ["DP-1"]},
        }
        tree, in_degree, _ = build_graph(config, monitors)

        positions, unprocessed = compute_positions(monitors, tree, in_degree, config)

        assert positions == {}
        assert set(unprocessed) == {"DP-1", "DP-2"}

    def test_anchor_monitor(self):
        """Test that anchor monitor (no placement rule) is processed first."""
        monitors = {
            "anchor": make_monitor("anchor", x=100, y=200),
            "DP-2": make_monitor("DP-2", x=0, y=0),
        }
        config = {
            "DP-2": {"rightOf": ["anchor"]},
        }
        tree, in_degree, _ = build_graph(config, monitors)

        positions, unprocessed = compute_positions(monitors, tree, in_degree, config)

        assert positions["anchor"] == (100, 200)
        assert positions["DP-2"] == (2020, 200)  # 100 + 1920
        assert unprocessed == []


class TestFindCyclePath:
    """Tests for find_cycle_path function."""

    def test_simple_cycle(self):
        """Test simple A -> B -> A cycle."""
        config = {
            "A": {"rightOf": ["B"]},
            "B": {"rightOf": ["A"]},
        }
        unprocessed = ["A", "B"]

        result = find_cycle_path(config, unprocessed)

        assert "A" in result
        assert "B" in result
        assert "->" in result

    def test_three_way_cycle(self):
        """Test A -> B -> C -> A cycle."""
        config = {
            "A": {"rightOf": ["B"]},
            "B": {"rightOf": ["C"]},
            "C": {"rightOf": ["A"]},
        }
        unprocessed = ["A", "B", "C"]

        result = find_cycle_path(config, unprocessed)

        assert "A" in result
        assert "B" in result
        assert "C" in result

    def test_no_clear_cycle(self):
        """Test when no clear cycle is found."""
        config = {
            "A": {"scale": 1.0},  # No dependency
            "B": {"scale": 1.0},  # No dependency
        }
        unprocessed = ["A", "B"]

        result = find_cycle_path(config, unprocessed)

        assert "unpositioned monitors" in result
        assert "A" in result
        assert "B" in result


class TestConstants:
    """Tests for module constants."""

    def test_monitor_props(self):
        """Test MONITOR_PROPS contains expected values."""
        assert "resolution" in MONITOR_PROPS
        assert "rate" in MONITOR_PROPS
        assert "scale" in MONITOR_PROPS
        assert "transform" in MONITOR_PROPS

    def test_max_cycle_path_length(self):
        """Test MAX_CYCLE_PATH_LENGTH is reasonable."""
        assert MAX_CYCLE_PATH_LENGTH > 0
        assert MAX_CYCLE_PATH_LENGTH <= 20
