"""Unit tests for pyprland.plugins.monitors.resolution module."""

import pytest

from pyprland.plugins.monitors.resolution import (
    get_monitor_by_pattern,
    resolve_placement_config,
)


def make_monitor(name, description=None, width=1920, height=1080, x=0, y=0, scale=1.0, transform=0):
    """Helper to create a monitor dict."""
    return {
        "name": name,
        "description": description or f"{name} Monitor Description",
        "width": width,
        "height": height,
        "x": x,
        "y": y,
        "scale": scale,
        "transform": transform,
        "refreshRate": 60,
    }


class TestGetMonitorByPattern:
    """Tests for get_monitor_by_pattern function."""

    def test_match_by_name(self):
        """Test matching by exact name."""
        monitors = [
            make_monitor("DP-1", "Dell Monitor"),
            make_monitor("DP-2", "Samsung Monitor"),
        ]
        description_db = {m["description"]: m for m in monitors}
        name_db = {m["name"]: m for m in monitors}

        result = get_monitor_by_pattern("DP-1", description_db, name_db)

        assert result is not None
        assert result["name"] == "DP-1"

    def test_match_by_description_substring(self):
        """Test matching by description substring."""
        monitors = [
            make_monitor("DP-1", "Dell U2720Q Monitor"),
            make_monitor("DP-2", "Samsung Odyssey G9"),
        ]
        description_db = {m["description"]: m for m in monitors}
        name_db = {m["name"]: m for m in monitors}

        result = get_monitor_by_pattern("Dell", description_db, name_db)

        assert result is not None
        assert result["name"] == "DP-1"

    def test_no_match(self):
        """Test when no monitor matches."""
        monitors = [
            make_monitor("DP-1", "Dell Monitor"),
        ]
        description_db = {m["description"]: m for m in monitors}
        name_db = {m["name"]: m for m in monitors}

        result = get_monitor_by_pattern("BenQ", description_db, name_db)

        assert result is None

    def test_cache_hit(self):
        """Test that cache is used."""
        monitors = [
            make_monitor("DP-1", "Dell Monitor"),
        ]
        description_db = {m["description"]: m for m in monitors}
        name_db = {m["name"]: m for m in monitors}
        cache = {"DP-1": monitors[0]}

        result = get_monitor_by_pattern("DP-1", description_db, name_db, cache)

        assert result is monitors[0]

    def test_cache_populated(self):
        """Test that cache is populated after lookup."""
        monitors = [
            make_monitor("DP-1", "Dell Monitor"),
        ]
        description_db = {m["description"]: m for m in monitors}
        name_db = {m["name"]: m for m in monitors}
        cache = {}

        result = get_monitor_by_pattern("DP-1", description_db, name_db, cache)

        assert result is not None
        assert "DP-1" in cache
        assert cache["DP-1"] == result

    def test_name_takes_precedence(self):
        """Test that exact name match takes precedence over description."""
        monitors = [
            make_monitor("Dell", "Samsung Monitor"),  # Name is Dell
            make_monitor("DP-1", "Dell Monitor"),  # Description contains Dell
        ]
        description_db = {m["description"]: m for m in monitors}
        name_db = {m["name"]: m for m in monitors}

        result = get_monitor_by_pattern("Dell", description_db, name_db)

        assert result is not None
        assert result["name"] == "Dell"


class TestResolvePlacementConfig:
    """Tests for resolve_placement_config function."""

    def test_basic_resolution(self):
        """Test basic pattern resolution."""
        monitors = [
            make_monitor("DP-1", "Dell Monitor"),
            make_monitor("DP-2", "Samsung Monitor"),
        ]
        placement_config = {
            "DP-2": {"rightOf": "DP-1"},
        }

        result = resolve_placement_config(placement_config, monitors)

        assert "DP-2" in result
        assert result["DP-2"]["rightOf"] == ["DP-1"]

    def test_description_pattern_resolution(self):
        """Test resolution using description patterns."""
        monitors = [
            make_monitor("DP-1", "Dell U2720Q Monitor"),
            make_monitor("DP-2", "Samsung Odyssey G9"),
        ]
        placement_config = {
            "Samsung": {"rightOf": "Dell"},
        }

        result = resolve_placement_config(placement_config, monitors)

        assert "DP-2" in result
        assert result["DP-2"]["rightOf"] == ["DP-1"]

    def test_preserves_monitor_props(self):
        """Test that monitor properties are preserved."""
        monitors = [
            make_monitor("DP-1", "Dell Monitor"),
        ]
        placement_config = {
            "DP-1": {
                "scale": 2.0,
                "resolution": "3840x2160",
                "rate": 144,
                "transform": 1,
            },
        }

        result = resolve_placement_config(placement_config, monitors)

        assert result["DP-1"]["scale"] == 2.0
        assert result["DP-1"]["resolution"] == "3840x2160"
        assert result["DP-1"]["rate"] == 144
        assert result["DP-1"]["transform"] == 1

    def test_multiple_targets_as_list(self):
        """Test that multiple targets are resolved as list."""
        monitors = [
            make_monitor("DP-1", "Dell Monitor"),
            make_monitor("DP-2", "Samsung Monitor"),
            make_monitor("DP-3", "BenQ Monitor"),
        ]
        placement_config = {
            "DP-3": {"rightOf": ["DP-1", "DP-2"]},
        }

        result = resolve_placement_config(placement_config, monitors)

        assert result["DP-3"]["rightOf"] == ["DP-1", "DP-2"]

    def test_unmatched_pattern_ignored(self):
        """Test that unmatched patterns are ignored."""
        monitors = [
            make_monitor("DP-1", "Dell Monitor"),
        ]
        placement_config = {
            "NonExistent": {"rightOf": "DP-1"},
            "DP-1": {"scale": 1.5},
        }

        result = resolve_placement_config(placement_config, monitors)

        assert "NonExistent" not in result
        assert "DP-1" in result

    def test_unmatched_target_ignored(self):
        """Test that unmatched targets are ignored."""
        monitors = [
            make_monitor("DP-1", "Dell Monitor"),
            make_monitor("DP-2", "Samsung Monitor"),
        ]
        placement_config = {
            "DP-2": {"rightOf": ["DP-1", "NonExistent"]},
        }

        result = resolve_placement_config(placement_config, monitors)

        assert result["DP-2"]["rightOf"] == ["DP-1"]

    def test_uses_provided_cache(self):
        """Test that provided cache is used and updated."""
        monitors = [
            make_monitor("DP-1", "Dell Monitor"),
            make_monitor("DP-2", "Samsung Monitor"),
        ]
        placement_config = {
            "DP-2": {"rightOf": "DP-1"},
        }
        cache = {}

        resolve_placement_config(placement_config, monitors, cache)

        # Cache should now contain the looked-up monitors
        assert "DP-1" in cache or "DP-2" in cache

    def test_empty_config(self):
        """Test with empty configuration."""
        monitors = [
            make_monitor("DP-1", "Dell Monitor"),
        ]
        placement_config = {}

        result = resolve_placement_config(placement_config, monitors)

        assert result == {}

    def test_empty_monitors(self):
        """Test with no monitors."""
        monitors = []
        placement_config = {
            "DP-1": {"rightOf": "DP-2"},
        }

        result = resolve_placement_config(placement_config, monitors)

        assert result == {}

    def test_mixed_props_and_rules(self):
        """Test config with both props and placement rules."""
        monitors = [
            make_monitor("DP-1", "Dell Monitor"),
            make_monitor("DP-2", "Samsung Monitor"),
        ]
        placement_config = {
            "DP-2": {
                "rightOf": "DP-1",
                "scale": 1.5,
                "rate": 120,
            },
        }

        result = resolve_placement_config(placement_config, monitors)

        assert result["DP-2"]["rightOf"] == ["DP-1"]
        assert result["DP-2"]["scale"] == 1.5
        assert result["DP-2"]["rate"] == 120
