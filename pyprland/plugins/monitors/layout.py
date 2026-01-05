"""Layout positioning logic."""

from typing import Any

from ...types import MonitorInfo

MONITOR_PROPS = {"resolution", "rate", "scale", "transform"}


def get_dims(mon: MonitorInfo, config: dict[str, Any] | None = None) -> tuple[int, int]:
    """Return the dimensions of the monitor."""
    if config is None:
        config = {}
    scale = config.get("scale", mon["scale"])
    transform = config.get("transform", mon["transform"])
    width = mon["width"]
    height = mon["height"]

    res = config.get("resolution")
    if res:
        try:
            if isinstance(res, str) and "x" in res:
                width, height = map(int, res.split("x"))
            elif isinstance(res, list | tuple):
                width, height = int(res[0]), int(res[1])
        except (ValueError, IndexError):
            pass

    width = int(width / scale)
    height = int(height / scale)

    if transform in [1, 3, 5, 7]:
        return height, width
    return width, height


def _place_left(ref_rect: tuple[int, int, int, int], mon_dim: tuple[int, int], rule: str) -> tuple[int, int]:
    """Place the monitor to the left of the reference."""
    ref_x, ref_y, _ref_w, ref_h = ref_rect
    mon_w, mon_h = mon_dim
    x = ref_x - mon_w
    y = ref_y
    if "bottom" in rule:
        y = ref_y + ref_h - mon_h
    elif "center" in rule or "middle" in rule:
        y = ref_y + (ref_h - mon_h) // 2
    return int(x), int(y)


def _place_right(ref_rect: tuple[int, int, int, int], mon_dim: tuple[int, int], rule: str) -> tuple[int, int]:
    """Place the monitor to the right of the reference."""
    ref_x, ref_y, ref_w, ref_h = ref_rect
    _mon_w, mon_h = mon_dim
    x = ref_x + ref_w
    y = ref_y
    if "bottom" in rule:
        y = ref_y + ref_h - mon_h
    elif "center" in rule or "middle" in rule:
        y = ref_y + (ref_h - mon_h) // 2
    return int(x), int(y)


def _place_top(ref_rect: tuple[int, int, int, int], mon_dim: tuple[int, int], rule: str) -> tuple[int, int]:
    """Place the monitor to the top of the reference."""
    ref_x, ref_y, ref_w, _ref_h = ref_rect
    mon_w, mon_h = mon_dim
    y = ref_y - mon_h
    x = ref_x
    if "right" in rule:
        x = ref_x + ref_w - mon_w
    elif "center" in rule or "middle" in rule:
        x = ref_x + (ref_w - mon_w) // 2
    return int(x), int(y)


def _place_bottom(ref_rect: tuple[int, int, int, int], mon_dim: tuple[int, int], rule: str) -> tuple[int, int]:
    """Place the monitor to the bottom of the reference."""
    ref_x, ref_y, ref_w, ref_h = ref_rect
    mon_w, _mon_h = mon_dim
    y = ref_y + ref_h
    x = ref_x
    if "right" in rule:
        x = ref_x + ref_w - mon_w
    elif "center" in rule or "middle" in rule:
        x = ref_x + (ref_w - mon_w) // 2
    return int(x), int(y)


def compute_xy(  # noqa: PLR0913
    ref_mon: MonitorInfo,
    mon: MonitorInfo,
    ref_rect: tuple[int, int],
    rule: str,
    ref_config: dict[str, Any] | None = None,
    mon_config: dict[str, Any] | None = None,
) -> tuple[int, int]:
    """Compute position of `mon` relative to `ref_mon` based on `rule`."""
    ref_x, ref_y = ref_rect
    ref_w, ref_h = get_dims(ref_mon, ref_config)
    mon_w, mon_h = get_dims(mon, mon_config)
    rule = rule.lower().replace("_", "").replace("-", "")

    rect = (ref_x, ref_y, ref_w, ref_h)
    mon_dim = (mon_w, mon_h)

    if "left" in rule:
        return _place_left(rect, mon_dim, rule)
    if "right" in rule:
        return _place_right(rect, mon_dim, rule)
    if "top" in rule:
        return _place_top(rect, mon_dim, rule)
    if "bottom" in rule:
        return _place_bottom(rect, mon_dim, rule)

    return ref_x, ref_y
