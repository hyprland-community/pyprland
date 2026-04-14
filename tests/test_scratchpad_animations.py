"""Unit tests for scratchpad animation coordinate computation.

Tests the Placement class (animations.py) and related helpers to ensure
on-screen and off-screen coordinates are computed correctly for all
animation directions, monitor offsets, margins, HiDPI scaling, and rotation.
"""

import pytest

from pyprland.plugins.scratchpads.animations import Placement
from pyprland.plugins.scratchpads.helpers import apply_offset, compute_offset, get_size


# ---------------------------------------------------------------------------
# Fixtures: monitors & clients
# ---------------------------------------------------------------------------


def _make_monitor(
    *,
    width=1920,
    height=1080,
    x=0,
    y=0,
    scale=1.0,
    transform=0,
    name="DP-1",
):
    """Create a minimal MonitorInfo-like dict."""
    return {
        "id": 0,
        "name": name,
        "description": "",
        "make": "",
        "model": "",
        "serial": "",
        "width": width,
        "height": height,
        "refreshRate": 60.0,
        "x": x,
        "y": y,
        "activeWorkspace": {"id": 1, "name": "1"},
        "specialWorkspace": {"id": 0, "name": ""},
        "reserved": [0, 0, 0, 0],
        "scale": scale,
        "transform": transform,
        "focused": True,
        "dpmsStatus": True,
        "vrr": False,
        "activelyTearing": False,
    }


def _make_client(*, width=800, height=600, at=(0, 0)):
    """Create a minimal ClientInfo-like dict."""
    return {
        "address": "0xABC",
        "mapped": True,
        "hidden": False,
        "at": list(at),
        "size": [width, height],
        "workspace": {"id": 1, "name": "1"},
        "floating": True,
        "monitor": 0,
        "class": "test",
        "title": "test",
        "initialClass": "test",
        "initialTitle": "test",
        "pid": 1,
        "xwayland": False,
        "pinned": False,
        "fullscreen": False,
        "fullscreenMode": 0,
        "fakeFullscreen": False,
        "grouped": [],
        "swallowing": "0x0",
        "focusHistoryID": 0,
    }


# ===========================================================================
# get_size
# ===========================================================================


class TestGetSize:
    """Tests for helpers.get_size."""

    def test_basic(self):
        mon = _make_monitor(width=1920, height=1080, scale=1.0)
        assert get_size(mon) == (1920, 1080)

    def test_scale_2x(self):
        mon = _make_monitor(width=3840, height=2160, scale=2.0)
        assert get_size(mon) == (1920, 1080)

    def test_scale_1_5x(self):
        mon = _make_monitor(width=3840, height=2160, scale=1.5)
        assert get_size(mon) == (2560, 1440)

    def test_rotated(self):
        """transform=1 (90° rotation) swaps width/height."""
        mon = _make_monitor(width=1920, height=1080, scale=1.0, transform=1)
        assert get_size(mon) == (1080, 1920)

    def test_rotated_with_scale(self):
        mon = _make_monitor(width=3840, height=2160, scale=2.0, transform=3)
        assert get_size(mon) == (1080, 1920)


# ===========================================================================
# compute_offset / apply_offset
# ===========================================================================


class TestOffsetHelpers:
    """Tests for compute_offset and apply_offset."""

    def test_compute_offset_basic(self):
        assert compute_offset((100, 200), (30, 50)) == (70, 150)

    def test_compute_offset_negative(self):
        assert compute_offset((10, 20), (30, 50)) == (-20, -30)

    def test_compute_offset_none_first(self):
        assert compute_offset(None, (30, 50)) == (0, 0)

    def test_compute_offset_none_second(self):
        assert compute_offset((30, 50), None) == (0, 0)

    def test_compute_offset_both_none(self):
        assert compute_offset(None, None) == (0, 0)

    def test_apply_offset_basic(self):
        assert apply_offset((100, 200), (10, -20)) == (110, 180)

    def test_apply_offset_zero(self):
        assert apply_offset((100, 200), (0, 0)) == (100, 200)


# ===========================================================================
# Placement – cardinal directions (scale=1, origin monitor)
# ===========================================================================


class TestPlacementBasicOrigin:
    """Placement on a 1920x1080 monitor at (0, 0), scale=1, no margin."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=1920, height=1080, x=0, y=0, scale=1.0)
        self.client = _make_client(width=800, height=600)

    def test_fromtop_no_margin(self):
        x, y = Placement.get("fromtop", self.mon, self.client, 0)
        # centered: (1920 - 800) / 2 = 560
        assert x == 560
        assert y == 0

    def test_frombottom_no_margin(self):
        x, y = Placement.get("frombottom", self.mon, self.client, 0)
        assert x == 560
        # bottom: 0 + 1080 - 600 = 480
        assert y == 480

    def test_fromleft_no_margin(self):
        x, y = Placement.get("fromleft", self.mon, self.client, 0)
        assert x == 0
        # centered: (1080 - 600) / 2 = 240
        assert y == 240

    def test_fromright_no_margin(self):
        x, y = Placement.get("fromright", self.mon, self.client, 0)
        # right: 1920 - 800 = 1120
        assert x == 1120
        assert y == 240


class TestPlacementWithMargin:
    """Integer pixel margin pushes window inward from the animation edge."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=1920, height=1080, x=0, y=0, scale=1.0)
        self.client = _make_client(width=800, height=600)

    def test_fromtop_margin_50(self):
        x, y = Placement.get("fromtop", self.mon, self.client, 50)
        assert x == 560
        # top edge + margin
        assert y == 50

    def test_frombottom_margin_50(self):
        x, y = Placement.get("frombottom", self.mon, self.client, 50)
        assert x == 560
        # 1080 - 600 - 50 = 430
        assert y == 430

    def test_fromleft_margin_50(self):
        x, y = Placement.get("fromleft", self.mon, self.client, 50)
        assert x == 50
        assert y == 240

    def test_fromright_margin_50(self):
        x, y = Placement.get("fromright", self.mon, self.client, 50)
        # 1920 - 800 - 50 = 1070
        assert x == 1070
        assert y == 240


# ===========================================================================
# Placement – monitor at non-origin offset
# ===========================================================================


class TestPlacementMonitorOffset:
    """Monitor positioned at (0, 1080) – a second monitor below another."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=3440, height=1440, x=0, y=1080, scale=1.0)
        self.client = _make_client(width=768, height=972)

    def test_fromtop(self):
        x, y = Placement.get("fromtop", self.mon, self.client, 0)
        # centered: (3440 - 768) / 2 + 0 = 1336
        assert x == 1336
        # y at monitor top: 1080
        assert y == 1080

    def test_frombottom(self):
        x, y = Placement.get("frombottom", self.mon, self.client, 0)
        assert x == 1336
        # 1080 + 1440 - 972 = 1548
        assert y == 1548

    def test_fromleft(self):
        x, y = Placement.get("fromleft", self.mon, self.client, 0)
        assert x == 0
        # centered: (1440 - 972) / 2 + 1080 = 234 + 1080 = 1314
        assert y == 1314

    def test_fromright(self):
        x, y = Placement.get("fromright", self.mon, self.client, 0)
        # 3440 - 768 + 0 = 2672
        assert x == 2672
        assert y == 1314

    def test_fromtop_with_margin(self):
        x, y = Placement.get("fromtop", self.mon, self.client, 20)
        assert x == 1336
        # 1080 + 20 = 1100
        assert y == 1100


# ===========================================================================
# Placement – side-offset monitor (multi-monitor horizontal layout)
# ===========================================================================


class TestPlacementSideOffset:
    """Monitor positioned at (1920, 0) – to the right of a 1920px primary."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=2560, height=1440, x=1920, y=0, scale=1.0)
        self.client = _make_client(width=1000, height=800)

    def test_fromleft(self):
        x, y = Placement.get("fromleft", self.mon, self.client, 0)
        # x at monitor left edge
        assert x == 1920
        # centered: (1440 - 800) / 2 + 0 = 320
        assert y == 320

    def test_fromright(self):
        x, y = Placement.get("fromright", self.mon, self.client, 0)
        # 2560 - 1000 + 1920 = 3480
        assert x == 3480
        assert y == 320

    def test_fromtop(self):
        x, y = Placement.get("fromtop", self.mon, self.client, 0)
        # centered: (2560 - 1000) / 2 + 1920 = 780 + 1920 = 2700
        assert x == 2700
        assert y == 0


# ===========================================================================
# Placement.get() error handling
# ===========================================================================


class TestPlacementGetErrors:
    """Placement.get() raises KeyError for unknown animation types."""

    def test_get_invalid_raises(self):
        mon = _make_monitor()
        client = _make_client()
        with pytest.raises(KeyError):
            Placement.get("fromdiagonal", mon, client, 0)


# ===========================================================================
# Placement.get_offscreen()
# ===========================================================================


class TestPlacementOffscreen:
    """Off-screen positions push window beyond adjacent monitors."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=1920, height=1080, x=0, y=0, scale=1.0)
        self.client = _make_client(width=800, height=600)

    def test_offscreen_fromtop(self):
        x, y = Placement.get_offscreen("fromtop", self.mon, self.client, 0)
        # x stays same as on-screen
        assert x == 560
        # y = mon_y - client_h - mon_h = 0 - 600 - 1080 = -1680
        assert y == -1680

    def test_offscreen_frombottom(self):
        x, y = Placement.get_offscreen("frombottom", self.mon, self.client, 0)
        assert x == 560
        # y = mon_y + mon_h + mon_h = 0 + 1080 + 1080 = 2160
        assert y == 2160

    def test_offscreen_fromleft(self):
        x, y = Placement.get_offscreen("fromleft", self.mon, self.client, 0)
        # x = mon_x - client_w - mon_w = 0 - 800 - 1920 = -2720
        assert x == -2720
        assert y == 240

    def test_offscreen_fromright(self):
        x, y = Placement.get_offscreen("fromright", self.mon, self.client, 0)
        # x = mon_x + mon_w + mon_w = 0 + 1920 + 1920 = 3840
        assert x == 3840
        assert y == 240


class TestPlacementOffscreenWithOffset:
    """Off-screen on a non-origin monitor preserves the axis not animated."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=3440, height=1440, x=0, y=1080, scale=1.0)
        self.client = _make_client(width=768, height=972)

    def test_offscreen_fromtop(self):
        x, y = Placement.get_offscreen("fromtop", self.mon, self.client, 0)
        # on-screen x = 1336
        assert x == 1336
        # y = 1080 - 972 - 1440 = -1332
        assert y == 1080 - 972 - 1440

    def test_offscreen_frombottom(self):
        x, y = Placement.get_offscreen("frombottom", self.mon, self.client, 0)
        assert x == 1336
        # y = 1080 + 1440 + 1440 = 3960
        assert y == 1080 + 1440 + 1440

    def test_offscreen_fromleft(self):
        x, y = Placement.get_offscreen("fromleft", self.mon, self.client, 0)
        # x = 0 - 768 - 3440 = -4208
        assert x == -4208
        # on-screen y = 1314
        assert y == 1314

    def test_offscreen_fromright(self):
        x, y = Placement.get_offscreen("fromright", self.mon, self.client, 0)
        # x = 0 + 3440 + 3440 = 6880
        assert x == 6880
        assert y == 1314


# ===========================================================================
# HiDPI (scale != 1.0)
# ===========================================================================


class TestPlacementHiDPI:
    """Verify coordinates with HiDPI scaling (scale=2.0).

    With scale=2.0 on a 3840x2160 panel, logical resolution is 1920x1080.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=3840, height=2160, x=0, y=0, scale=2.0)
        # get_size => (1920, 1080)
        self.client = _make_client(width=800, height=600)

    def test_fromtop(self):
        x, y = Placement.get("fromtop", self.mon, self.client, 0)
        # centered: (1920 - 800) / 2 = 560
        assert x == 560
        assert y == 0

    def test_frombottom(self):
        x, y = Placement.get("frombottom", self.mon, self.client, 0)
        assert x == 560
        # 0 + 1080 - 600 = 480
        assert y == 480

    def test_fromleft(self):
        x, y = Placement.get("fromleft", self.mon, self.client, 0)
        assert x == 0
        # (1080 - 600) / 2 = 240
        assert y == 240

    def test_fromright(self):
        x, y = Placement.get("fromright", self.mon, self.client, 0)
        # 1920 - 800 = 1120
        assert x == 1120
        assert y == 240

    def test_offscreen_fromtop(self):
        x, y = Placement.get_offscreen("fromtop", self.mon, self.client, 0)
        # mon_h via get_size = 1080
        # y = 0 - 600 - 1080 = -1680
        assert y == -1680

    def test_offscreen_fromright(self):
        x, y = Placement.get_offscreen("fromright", self.mon, self.client, 0)
        # mon_w via get_size = 1920
        # x = 0 + 1920 + 1920 = 3840
        assert x == 3840


class TestPlacementHiDPI_1_5x:
    """Verify with fractional scaling (1.5x)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=3840, height=2160, x=0, y=0, scale=1.5)
        # get_size => (2560, 1440)
        self.client = _make_client(width=1000, height=800)

    def test_fromtop(self):
        x, y = Placement.get("fromtop", self.mon, self.client, 0)
        # centered: (2560 - 1000) / 2 = 780
        assert x == 780
        assert y == 0

    def test_frombottom(self):
        x, y = Placement.get("frombottom", self.mon, self.client, 0)
        assert x == 780
        # 1440 - 800 = 640
        assert y == 640

    def test_fromright(self):
        x, y = Placement.get("fromright", self.mon, self.client, 0)
        # 2560 - 1000 = 1560
        assert x == 1560
        # (1440 - 800) / 2 = 320
        assert y == 320


# ===========================================================================
# Rotated monitor (transform=1 means 90° CW)
# ===========================================================================


class TestPlacementRotated:
    """On a rotated monitor, get_size swaps w/h.

    Physical 1920x1080 with transform=1 => logical 1080x1920.
    """

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=1920, height=1080, x=0, y=0, scale=1.0, transform=1)
        # get_size => (1080, 1920)
        self.client = _make_client(width=600, height=800)

    def test_fromtop(self):
        x, y = Placement.get("fromtop", self.mon, self.client, 0)
        # centered: (1080 - 600) / 2 = 240
        assert x == 240
        assert y == 0

    def test_frombottom(self):
        x, y = Placement.get("frombottom", self.mon, self.client, 0)
        assert x == 240
        # mon_h = 1920 (after swap), 1920 - 800 = 1120
        assert y == 1120

    def test_fromleft(self):
        x, y = Placement.get("fromleft", self.mon, self.client, 0)
        assert x == 0
        # centered: (1920 - 800) / 2 = 560
        assert y == 560

    def test_fromright(self):
        x, y = Placement.get("fromright", self.mon, self.client, 0)
        # mon_w = 1080 (after swap), 1080 - 600 = 480
        assert x == 480
        assert y == 560

    def test_offscreen_fromtop(self):
        x, y = Placement.get_offscreen("fromtop", self.mon, self.client, 0)
        # mon_h = 1920 from get_size
        # y = 0 - 800 - 1920 = -2720
        assert y == -2720

    def test_offscreen_fromleft(self):
        x, y = Placement.get_offscreen("fromleft", self.mon, self.client, 0)
        # mon_w = 1080 from get_size
        # x = 0 - 600 - 1080 = -1680
        assert x == -1680


# ===========================================================================
# Edge cases: client same size as monitor, tiny margins
# ===========================================================================


class TestPlacementEdgeCases:
    """Edge cases for coordinate computation."""

    def test_client_fills_monitor(self):
        """Client same size as monitor -> centered at (0,0)."""
        mon = _make_monitor(width=1920, height=1080)
        client = _make_client(width=1920, height=1080)
        for direction in ("fromtop", "frombottom", "fromleft", "fromright"):
            x, y = Placement.get(direction, mon, client, 0)
            assert (x, y) == (0, 0), f"{direction}: expected (0, 0)"

    def test_very_small_client(self):
        """Small client is still centered properly."""
        mon = _make_monitor(width=1920, height=1080)
        client = _make_client(width=100, height=50)
        x, y = Placement.get("fromtop", mon, client, 0)
        assert x == 910  # (1920 - 100) / 2
        assert y == 0

    def test_client_wider_than_monitor(self):
        """Client wider than monitor -> negative centering offset (still works)."""
        mon = _make_monitor(width=1920, height=1080)
        client = _make_client(width=2000, height=600)
        x, y = Placement.get("fromtop", mon, client, 0)
        # (1920 - 2000) / 2 = -40
        assert x == -40
        assert y == 0

    def test_string_percentage_margin(self):
        """String margin '10%' is converted via convert_monitor_dimension."""
        mon = _make_monitor(width=1920, height=1080, scale=1.0)
        client = _make_client(width=800, height=600)
        x, y = Placement.get("fromtop", mon, client, "10%")
        assert x == 560
        # 10% of 1080 = 108
        assert y == 108

    def test_string_pixel_margin(self):
        """String margin '30px' is converted to integer 30."""
        mon = _make_monitor(width=1920, height=1080, scale=1.0)
        client = _make_client(width=800, height=600)
        x, y = Placement.get("fromtop", mon, client, "30px")
        assert x == 560
        assert y == 30

    def test_percentage_margin_with_scale(self):
        """Percentage margin respects HiDPI scale.

        fromtop passes get_size(monitor)[1] as ref_value to convert_monitor_dimension.
        get_size already divides by scale: 2160/2.0 = 1080.
        Then convert_monitor_dimension does: int(1080 / 2.0 * 10 / 100) = 54.
        """
        mon = _make_monitor(width=3840, height=2160, scale=2.0)
        client = _make_client(width=800, height=600)
        x, y = Placement.get("fromtop", mon, client, "10%")
        assert y == 54

    def test_margin_direction_consistency(self):
        """Margin pushes inward from the animation edge for all directions."""
        mon = _make_monitor(width=1920, height=1080)
        client = _make_client(width=800, height=600)
        margin = 100

        _, y_top = Placement.get("fromtop", mon, client, margin)
        _, y_bottom = Placement.get("frombottom", mon, client, margin)
        x_left, _ = Placement.get("fromleft", mon, client, margin)
        x_right, _ = Placement.get("fromright", mon, client, margin)

        _, y_top0 = Placement.get("fromtop", mon, client, 0)
        _, y_bottom0 = Placement.get("frombottom", mon, client, 0)
        x_left0, _ = Placement.get("fromleft", mon, client, 0)
        x_right0, _ = Placement.get("fromright", mon, client, 0)

        # Margin pushes top down, bottom up, left right, right left
        assert y_top > y_top0
        assert y_bottom < y_bottom0
        assert x_left > x_left0
        assert x_right < x_right0


# ===========================================================================
# Symmetry and consistency checks
# ===========================================================================


class TestPlacementSymmetry:
    """Cross-direction consistency checks."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=1920, height=1080, x=0, y=0)
        self.client = _make_client(width=800, height=600)

    def test_top_bottom_centering_matches(self):
        """fromtop and frombottom produce the same x (centered)."""
        x_top, _ = Placement.get("fromtop", self.mon, self.client, 0)
        x_bot, _ = Placement.get("frombottom", self.mon, self.client, 0)
        assert x_top == x_bot

    def test_left_right_centering_matches(self):
        """fromleft and fromright produce the same y (centered)."""
        _, y_left = Placement.get("fromleft", self.mon, self.client, 0)
        _, y_right = Placement.get("fromright", self.mon, self.client, 0)
        assert y_left == y_right

    def test_offscreen_preserves_cross_axis(self):
        """Off-screen position keeps the non-animated axis unchanged."""
        for anim in ("fromtop", "frombottom"):
            on_x, _ = Placement.get(anim, self.mon, self.client, 0)
            off_x, _ = Placement.get_offscreen(anim, self.mon, self.client, 0)
            assert on_x == off_x, f"{anim}: x should be preserved off-screen"

        for anim in ("fromleft", "fromright"):
            _, on_y = Placement.get(anim, self.mon, self.client, 0)
            _, off_y = Placement.get_offscreen(anim, self.mon, self.client, 0)
            assert on_y == off_y, f"{anim}: y should be preserved off-screen"

    def test_offscreen_is_outside_monitor(self):
        """Off-screen positions are beyond the monitor bounds."""
        mon_w, mon_h = get_size(self.mon)
        client_w, client_h = self.client["size"]

        _, y_top = Placement.get_offscreen("fromtop", self.mon, self.client, 0)
        assert y_top + client_h <= self.mon["y"], "fromtop offscreen should be above monitor"

        _, y_bot = Placement.get_offscreen("frombottom", self.mon, self.client, 0)
        assert y_bot >= self.mon["y"] + mon_h, "frombottom offscreen should be below monitor"

        x_left, _ = Placement.get_offscreen("fromleft", self.mon, self.client, 0)
        assert x_left + client_w <= self.mon["x"], "fromleft offscreen should be left of monitor"

        x_right, _ = Placement.get_offscreen("fromright", self.mon, self.client, 0)
        assert x_right >= self.mon["x"] + mon_w, "fromright offscreen should be right of monitor"


# ===========================================================================
# Diagonal placements
# ===========================================================================


class TestPlacementDiagonalBasic:
    """Diagonal placements on a 1920x1080 monitor at (0, 0), scale=1, no margin."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=1920, height=1080, x=0, y=0, scale=1.0)
        self.client = _make_client(width=800, height=600)

    def test_fromtopleft(self):
        x, y = Placement.get("fromtopleft", self.mon, self.client, 0)
        assert x == 0
        assert y == 0

    def test_fromtopright(self):
        x, y = Placement.get("fromtopright", self.mon, self.client, 0)
        # 1920 - 800 = 1120
        assert x == 1120
        assert y == 0

    def test_frombottomleft(self):
        x, y = Placement.get("frombottomleft", self.mon, self.client, 0)
        assert x == 0
        # 1080 - 600 = 480
        assert y == 480

    def test_frombottomright(self):
        x, y = Placement.get("frombottomright", self.mon, self.client, 0)
        assert x == 1120
        assert y == 480


class TestPlacementDiagonalWithMargin:
    """Diagonal placements with margins push inward from both edges."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=1920, height=1080, x=0, y=0, scale=1.0)
        self.client = _make_client(width=800, height=600)

    def test_fromtopleft_margin(self):
        x, y = Placement.get("fromtopleft", self.mon, self.client, 50)
        assert x == 50
        assert y == 50

    def test_fromtopright_margin(self):
        x, y = Placement.get("fromtopright", self.mon, self.client, 50)
        # 1920 - 800 - 50 = 1070
        assert x == 1070
        assert y == 50

    def test_frombottomleft_margin(self):
        x, y = Placement.get("frombottomleft", self.mon, self.client, 50)
        assert x == 50
        # 1080 - 600 - 50 = 430
        assert y == 430

    def test_frombottomright_margin(self):
        x, y = Placement.get("frombottomright", self.mon, self.client, 50)
        assert x == 1070
        assert y == 430


class TestPlacementDiagonalMonitorOffset:
    """Diagonal placements on a monitor at (0, 1080)."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=3440, height=1440, x=0, y=1080, scale=1.0)
        self.client = _make_client(width=768, height=972)

    def test_fromtopleft(self):
        x, y = Placement.get("fromtopleft", self.mon, self.client, 0)
        assert x == 0
        assert y == 1080

    def test_fromtopright(self):
        x, y = Placement.get("fromtopright", self.mon, self.client, 0)
        # 3440 - 768 = 2672
        assert x == 2672
        assert y == 1080

    def test_frombottomleft(self):
        x, y = Placement.get("frombottomleft", self.mon, self.client, 0)
        assert x == 0
        # 1080 + 1440 - 972 = 1548
        assert y == 1548

    def test_frombottomright(self):
        x, y = Placement.get("frombottomright", self.mon, self.client, 0)
        assert x == 2672
        assert y == 1548

    def test_fromtopright_with_margin(self):
        x, y = Placement.get("fromtopright", self.mon, self.client, 20)
        # 3440 - 768 - 20 + 0 = 2652
        assert x == 2652
        # 1080 + 20 = 1100
        assert y == 1100


class TestPlacementDiagonalOffscreen:
    """Off-screen positions for diagonal placements push both axes."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=1920, height=1080, x=0, y=0, scale=1.0)
        self.client = _make_client(width=800, height=600)

    def test_fromtopleft_offscreen(self):
        x, y = Placement.get_offscreen("fromtopleft", self.mon, self.client, 0)
        # x = 0 - 800 - 1920 = -2720
        assert x == -2720
        # y = 0 - 600 - 1080 = -1680
        assert y == -1680

    def test_fromtopright_offscreen(self):
        x, y = Placement.get_offscreen("fromtopright", self.mon, self.client, 0)
        # x = 0 + 1920 + 1920 = 3840
        assert x == 3840
        # y = 0 - 600 - 1080 = -1680
        assert y == -1680

    def test_frombottomleft_offscreen(self):
        x, y = Placement.get_offscreen("frombottomleft", self.mon, self.client, 0)
        # x = 0 - 800 - 1920 = -2720
        assert x == -2720
        # y = 0 + 1080 + 1080 = 2160
        assert y == 2160

    def test_frombottomright_offscreen(self):
        x, y = Placement.get_offscreen("frombottomright", self.mon, self.client, 0)
        # x = 0 + 1920 + 1920 = 3840
        assert x == 3840
        # y = 0 + 1080 + 1080 = 2160
        assert y == 2160


class TestPlacementDiagonalOffscreenMonitorOffset:
    """Off-screen diagonal positions on a non-origin monitor."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=2560, height=1440, x=1920, y=0, scale=1.0)
        self.client = _make_client(width=1000, height=800)

    def test_fromtopleft_offscreen(self):
        x, y = Placement.get_offscreen("fromtopleft", self.mon, self.client, 0)
        # x = 1920 - 1000 - 2560 = -1640
        assert x == -1640
        # y = 0 - 800 - 1440 = -2240
        assert y == -2240

    def test_frombottomright_offscreen(self):
        x, y = Placement.get_offscreen("frombottomright", self.mon, self.client, 0)
        # x = 1920 + 2560 + 2560 = 7040
        assert x == 7040
        # y = 0 + 1440 + 1440 = 2880
        assert y == 2880


class TestPlacementDiagonalSymmetry:
    """Symmetry checks for diagonal placements."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.mon = _make_monitor(width=1920, height=1080, x=0, y=0, scale=1.0)
        self.client = _make_client(width=800, height=600)

    def test_fromtopleft_fromtopright_y_matches(self):
        """fromtopleft and fromtopright share the same y (both at top edge)."""
        _, y_tl = Placement.get("fromtopleft", self.mon, self.client, 0)
        _, y_tr = Placement.get("fromtopright", self.mon, self.client, 0)
        assert y_tl == y_tr

    def test_frombottomleft_frombottomright_y_matches(self):
        """frombottomleft and frombottomright share the same y (both at bottom edge)."""
        _, y_bl = Placement.get("frombottomleft", self.mon, self.client, 0)
        _, y_br = Placement.get("frombottomright", self.mon, self.client, 0)
        assert y_bl == y_br

    def test_fromtopleft_frombottomleft_x_matches(self):
        """fromtopleft and frombottomleft share the same x (both at left edge)."""
        x_tl, _ = Placement.get("fromtopleft", self.mon, self.client, 0)
        x_bl, _ = Placement.get("frombottomleft", self.mon, self.client, 0)
        assert x_tl == x_bl

    def test_fromtopright_frombottomright_x_matches(self):
        """fromtopright and frombottomright share the same x (both at right edge)."""
        x_tr, _ = Placement.get("fromtopright", self.mon, self.client, 0)
        x_br, _ = Placement.get("frombottomright", self.mon, self.client, 0)
        assert x_tr == x_br

    def test_diagonal_corners_match_cardinal_edges(self):
        """Diagonal y matches cardinal top/bottom y; diagonal x matches cardinal left/right x."""
        m = 50
        _, y_top = Placement.get("fromtop", self.mon, self.client, m)
        _, y_bot = Placement.get("frombottom", self.mon, self.client, m)
        x_left, _ = Placement.get("fromleft", self.mon, self.client, m)
        x_right, _ = Placement.get("fromright", self.mon, self.client, m)

        _, y_tl = Placement.get("fromtopleft", self.mon, self.client, m)
        x_tl, _ = Placement.get("fromtopleft", self.mon, self.client, m)
        _, y_br = Placement.get("frombottomright", self.mon, self.client, m)
        x_br, _ = Placement.get("frombottomright", self.mon, self.client, m)

        assert y_tl == y_top, "fromtopleft y should match fromtop y"
        assert y_br == y_bot, "frombottomright y should match frombottom y"
        assert x_tl == x_left, "fromtopleft x should match fromleft x"
        assert x_br == x_right, "frombottomright x should match fromright x"

    def test_offscreen_diagonal_outside_monitor(self):
        """Off-screen diagonal positions are fully beyond monitor bounds on both axes."""
        mon_w, mon_h = get_size(self.mon)
        client_w, client_h = self.client["size"]

        for diag in ("fromtopleft", "fromtopright", "frombottomleft", "frombottomright"):
            x, y = Placement.get_offscreen(diag, self.mon, self.client, 0)
            if "top" in diag:
                assert y + client_h <= self.mon["y"], f"{diag}: should be above monitor"
            else:
                assert y >= self.mon["y"] + mon_h, f"{diag}: should be below monitor"
            if "left" in diag:
                assert x + client_w <= self.mon["x"], f"{diag}: should be left of monitor"
            else:
                assert x >= self.mon["x"] + mon_w, f"{diag}: should be right of monitor"

    def test_client_fills_monitor_diagonals(self):
        """Full-size client at all diagonal corners is at (0, 0)."""
        mon = _make_monitor(width=1920, height=1080)
        client = _make_client(width=1920, height=1080)
        for direction in ("fromtopleft", "fromtopright", "frombottomleft", "frombottomright"):
            x, y = Placement.get(direction, mon, client, 0)
            assert (x, y) == (0, 0), f"{direction} with full-size client should be (0, 0)"
