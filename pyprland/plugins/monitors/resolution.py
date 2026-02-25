"""Monitor pattern matching and name resolution."""

from typing import Any

from ...models import MonitorInfo
from .schema import MONITOR_PROPS


def get_monitor_by_pattern(
    pattern: str,
    description_db: dict[str, MonitorInfo],
    name_db: dict[str, MonitorInfo],
    cache: dict[str, MonitorInfo] | None = None,
) -> MonitorInfo | None:
    """Find a monitor by pattern (exact name or description substring).

    Args:
        pattern: Pattern to search for (monitor name or description substring)
        description_db: Mapping of descriptions to monitor info
        name_db: Mapping of names to monitor info
        cache: Optional cache to store/retrieve results

    Returns:
        MonitorInfo if found, None otherwise
    """
    if cache is not None:
        cached = cache.get(pattern)
        if cached:
            return cached

    result: MonitorInfo | None = None

    if pattern in name_db:
        result = name_db[pattern]
    else:
        for full_descr, mon in description_db.items():
            if pattern in full_descr:
                result = mon
                break

    if result is not None and cache is not None:
        cache[pattern] = result

    return result


def resolve_placement_config(
    placement_config: dict[str, Any],
    monitors: list[MonitorInfo],
    cache: dict[str, MonitorInfo] | None = None,
) -> dict[str, dict[str, Any]]:
    """Resolve configuration patterns to actual monitor names.

    Takes placement configuration with patterns (monitor names or description
    substrings) and resolves them to actual connected monitor names.

    Args:
        placement_config: Raw placement configuration from plugin config
        monitors: List of available monitors
        cache: Optional cache for pattern lookups

    Returns:
        Configuration dict keyed by actual monitor names with resolved targets
    """
    monitors_by_descr = {m["description"]: m for m in monitors}
    monitors_by_name = {m["name"]: m for m in monitors}

    cleaned_config: dict[str, dict[str, Any]] = {}

    for pat, rules in placement_config.items():
        # Find the subject monitor
        mon = get_monitor_by_pattern(pat, monitors_by_descr, monitors_by_name, cache)
        if not mon:
            continue

        name = mon["name"]
        cleaned_config[name] = {}

        for rule_key, rule_val in rules.items():
            if rule_key in MONITOR_PROPS:
                cleaned_config[name][rule_key] = rule_val
                continue

            # Resolve target monitors in the rule
            targets = []
            for target_pat in [rule_val] if isinstance(rule_val, str) else rule_val:
                target_mon = get_monitor_by_pattern(target_pat, monitors_by_descr, monitors_by_name, cache)
                if target_mon:
                    targets.append(target_mon["name"])

            if targets:
                cleaned_config[name][rule_key] = targets

    return cleaned_config
