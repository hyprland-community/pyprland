"""Layout positioning logic."""

from collections import defaultdict
from typing import Any

from ...models import MonitorInfo
from .schema import MONITOR_PROPS

MAX_CYCLE_PATH_LENGTH = 10


def get_dims(mon: MonitorInfo, config: dict[str, Any] | None = None) -> tuple[int, int]:
    """Return the dimensions of the monitor.

    Args:
        mon: The monitor information.
        config: The monitor configuration.

    Returns:
        tuple[int, int]: The (width, height) of the monitor.
    """
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
    """Place the monitor to the left of the reference.

    Args:
        ref_rect: The (x, y, width, height) of the reference monitor.
        mon_dim: The (width, height) of the monitor to place.
        rule: The placement rule (e.g. "left", "left-center", "left-end").

    Returns:
        tuple[int, int]: The (x, y) coordinates for the new monitor.
    """
    ref_x, ref_y, _ref_w, ref_h = ref_rect
    mon_w, mon_h = mon_dim
    x = ref_x - mon_w
    y = ref_y
    if "end" in rule:
        y = ref_y + ref_h - mon_h
    elif "center" in rule or "middle" in rule:
        y = ref_y + (ref_h - mon_h) // 2
    return int(x), int(y)


def _place_right(ref_rect: tuple[int, int, int, int], mon_dim: tuple[int, int], rule: str) -> tuple[int, int]:
    """Place the monitor to the right of the reference.

    Args:
        ref_rect: The (x, y, width, height) of the reference monitor.
        mon_dim: The (width, height) of the monitor to place.
        rule: The placement rule (e.g. "right", "right-center", "right-end").

    Returns:
        tuple[int, int]: The (x, y) coordinates for the new monitor.
    """
    ref_x, ref_y, ref_w, ref_h = ref_rect
    _mon_w, mon_h = mon_dim
    x = ref_x + ref_w
    y = ref_y
    if "end" in rule:
        y = ref_y + ref_h - mon_h
    elif "center" in rule or "middle" in rule:
        y = ref_y + (ref_h - mon_h) // 2
    return int(x), int(y)


def _place_top(ref_rect: tuple[int, int, int, int], mon_dim: tuple[int, int], rule: str) -> tuple[int, int]:
    """Place the monitor to the top of the reference.

    Args:
        ref_rect: The (x, y, width, height) of the reference monitor.
        mon_dim: The (width, height) of the monitor to place.
        rule: The placement rule (e.g. "top", "top-center", "top-end").

    Returns:
        tuple[int, int]: The (x, y) coordinates for the new monitor.
    """
    ref_x, ref_y, ref_w, _ref_h = ref_rect
    mon_w, mon_h = mon_dim
    y = ref_y - mon_h
    x = ref_x
    if "end" in rule:
        x = ref_x + ref_w - mon_w
    elif "center" in rule or "middle" in rule:
        x = ref_x + (ref_w - mon_w) // 2
    return int(x), int(y)


def _place_bottom(ref_rect: tuple[int, int, int, int], mon_dim: tuple[int, int], rule: str) -> tuple[int, int]:
    """Place the monitor to the bottom of the reference.

    Args:
        ref_rect: The (x, y, width, height) of the reference monitor.
        mon_dim: The (width, height) of the monitor to place.
        rule: The placement rule (e.g. "bottom", "bottom-center", "bottom-end").

    Returns:
        tuple[int, int]: The (x, y) coordinates for the new monitor.
    """
    ref_x, ref_y, ref_w, ref_h = ref_rect
    mon_w, _mon_h = mon_dim
    y = ref_y + ref_h
    x = ref_x
    if "end" in rule:
        x = ref_x + ref_w - mon_w
    elif "center" in rule or "middle" in rule:
        x = ref_x + (ref_w - mon_w) // 2
    return int(x), int(y)


def compute_xy(
    ref_rect: tuple[int, int, int, int],
    mon_dim: tuple[int, int],
    rule: str,
) -> tuple[int, int]:
    """Compute position of a monitor relative to a reference monitor.

    Args:
        ref_rect: The (x, y, width, height) of the reference monitor.
        mon_dim: The (width, height) of the monitor to place.
        rule: The placement rule (e.g. "left", "right", "top-center").

    Returns:
        tuple[int, int]: The (x, y) coordinates for the new monitor.
    """
    rule = rule.lower().replace("_", "").replace("-", "")

    if "left" in rule:
        return _place_left(ref_rect, mon_dim, rule)
    if "right" in rule:
        return _place_right(ref_rect, mon_dim, rule)
    if "top" in rule:
        return _place_top(ref_rect, mon_dim, rule)
    if "bottom" in rule:
        return _place_bottom(ref_rect, mon_dim, rule)

    return ref_rect[0], ref_rect[1]


# --- Graph and Position Computation ---


def build_graph(
    config: dict[str, Any],
    monitors_by_name: dict[str, MonitorInfo],
) -> tuple[dict[str, list[tuple[str, str]]], dict[str, int], list[tuple[str, str, list[str]]]]:
    """Build the dependency graph for monitor layout.

    Args:
        config: Configuration dictionary (resolved monitor names -> rules)
        monitors_by_name: Mapping of monitor names to info

    Returns:
        Tuple of:
        - tree: Dependency graph (parent -> list of (child, rule))
        - in_degree: In-degree count for each monitor
        - multi_target_info: List of (name, rule, targets) for logging when multiple targets specified
    """
    tree: dict[str, list[tuple[str, str]]] = defaultdict(list)
    in_degree: dict[str, int] = defaultdict(int)
    multi_target_info: list[tuple[str, str, list[str]]] = []

    for name in monitors_by_name:
        in_degree[name] = 0

    for name, rules in config.items():
        for rule_name, target_names in rules.items():
            if rule_name in MONITOR_PROPS or rule_name == "disables":
                continue
            if len(target_names) > 1:
                multi_target_info.append((name, rule_name, target_names))
            target_name = target_names[0] if target_names else None
            if target_name and target_name in monitors_by_name:
                tree[target_name].append((name, rule_name))
                in_degree[name] += 1

    return tree, in_degree, multi_target_info


def compute_positions(
    monitors_by_name: dict[str, MonitorInfo],
    tree: dict[str, list[tuple[str, str]]],
    in_degree: dict[str, int],
    config: dict[str, Any],
) -> tuple[dict[str, tuple[int, int]], list[str]]:
    """Compute the positions of all monitors using topological sort.

    Args:
        monitors_by_name: Mapping of monitor names to info
        tree: Dependency graph (parent -> list of (child, rule))
        in_degree: In-degree count for each monitor
        config: Configuration dictionary

    Returns:
        Tuple of:
        - positions: Computed (x, y) positions for each monitor
        - unprocessed: List of monitor names that couldn't be positioned (cycle detected)
    """
    queue = [name for name in monitors_by_name if in_degree[name] == 0]
    positions: dict[str, tuple[int, int]] = {}
    for name in queue:
        positions[name] = (monitors_by_name[name]["x"], monitors_by_name[name]["y"])

    processed = set()
    while queue:
        ref_name = queue.pop(0)
        if ref_name in processed:
            continue
        processed.add(ref_name)

        for child_name, rule in tree[ref_name]:
            ref_rect = (
                *positions[ref_name],
                *get_dims(monitors_by_name[ref_name], config.get(ref_name, {})),
            )

            mon_dim = get_dims(monitors_by_name[child_name], config.get(child_name, {}))

            positions[child_name] = compute_xy(
                ref_rect,
                mon_dim,
                rule,
            )

            in_degree[child_name] -= 1
            if in_degree[child_name] == 0:
                queue.append(child_name)

    # Return unprocessed monitors (indicates circular dependencies)
    unprocessed = [name for name in monitors_by_name if name not in positions]
    return positions, unprocessed


def find_cycle_path(config: dict[str, Any], unprocessed: list[str]) -> str:
    """Find and format the cycle path for unprocessed monitors.

    Args:
        config: Configuration dictionary
        unprocessed: List of monitor names that couldn't be positioned

    Returns:
        Human-readable cycle path string
    """
    # Build reverse lookup: monitor -> target it depends on
    depends_on: dict[str, str] = {}
    for name, rules in config.items():
        for rule_name, target_names in rules.items():
            if rule_name in MONITOR_PROPS or rule_name == "disables":
                continue
            if target_names:
                depends_on[name] = target_names[0]

    # Trace cycle starting from first unprocessed monitor
    start = unprocessed[0]
    path = [start]
    current = depends_on.get(start)

    while current and current not in path and len(path) < MAX_CYCLE_PATH_LENGTH:
        path.append(current)
        current = depends_on.get(current)

    if current and current in path:
        # Found the cycle - show it
        cycle_start = path.index(current)
        cycle = path[cycle_start:] + [current]
        return " -> ".join(cycle)

    # No clear cycle found, just list unprocessed
    return f"unpositioned monitors: {', '.join(unprocessed)}"
