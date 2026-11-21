"""Semantic color palette and priority-order resolution from YAML rules."""

from collections.abc import Mapping

from app.dashboard.schemas import ThemePalettes
from app.processor.rule_loader import DomainRule

_SEMANTIC_LIGHT: dict[str, str] = {
    "bug": "#b51c3c",
    "feature": "#1a7a62",
    "task": "#005e9e",
    "epic": "#8a0ea8",
    "active": "#1a7a62",
    "waiting": "#b06000",
    "completed": "#8a0ea8",
    "stale": "#b51c3c",
    "opened": "#005e9e",
    "closed": "#1a7a62",
    "primary": "#ff512f",
    "accent": "#006ea3",
    "neutral": "#3d5370",
    "critical": "#F43F5E",
    "high": "#FB923C",
    "medium": "#FBBF24",
    "low": "#1a7a62",
    "unset": "#3d5370",
    "p1": "#b51c3c",
    "p2": "#b06000",
    "p3": "#1a7a62",
    "ms_complete": "#006ea3",
    "ms_incomplete": "#b06000",
    "ms_on_track": "#1a7a62",
    "ms_overdue": "#b51c3c",
    "ms_highlight": "#b06000",
    "ms_unscheduled": "#4f6585",
    "now_marker": "#dd2476",
}

_SEMANTIC_DARK: dict[str, str] = {
    "bug": "#f5576c",
    "feature": "#56d4b0",
    "task": "#4facfe",
    "epic": "#c76bff",
    "active": "#56d4b0",
    "waiting": "#f4a44a",
    "completed": "#c76bff",
    "stale": "#f5576c",
    "opened": "#4facfe",
    "closed": "#56d4b0",
    "primary": "#ff512f",
    "accent": "#00f2fe",
    "neutral": "#7a8fa8",
    "critical": "#e06565",
    "high": "#e88236",
    "medium": "#f4a44a",
    "low": "#56d4b0",
    "unset": "#7a8fa8",
    "p1": "#dd2476",
    "p2": "#f4a44a",
    "p3": "#56d4b0",
    "ms_complete": "#00f2fe",
    "ms_incomplete": "#f4a44a",
    "ms_on_track": "#56d4b0",
    "ms_overdue": "#f5576c",
    "ms_highlight": "#f4a44a",
    "ms_unscheduled": "#9fb2cc",
    "now_marker": "#dd2476",
}


def default_palettes() -> tuple[dict[str, str], dict[str, str]]:
    """Return copies of the built-in (light, dark) semantic color maps."""
    return dict(_SEMANTIC_LIGHT), dict(_SEMANTIC_DARK)


def _normalize_color_mapping(value: object) -> dict[str, str]:
    if not isinstance(value, Mapping):
        return {}
    return {str(k).strip().lower(): str(v) for k, v in value.items() if isinstance(v, str)}


def find_default_rule(rules: Mapping[int, DomainRule]) -> DomainRule | None:
    """Return the rule set that applies to all projects without their own.

    Prefers the rule set registered for "all other projects" (empty
    ``project_ids``), then one whose team is ``default``, then the first rule
    set. Returns None when there are no rule sets.
    """
    if 0 in rules:
        return rules[0]
    for rule in rules.values():
        if rule.team == "default":
            return rule
    return next(iter(rules.values()), None)


def resolve_palettes(rules: Mapping[int, DomainRule]) -> ThemePalettes:
    """Resolve light/dark semantic color maps and priority order from rules."""
    light = dict(_SEMANTIC_LIGHT)
    dark = dict(_SEMANTIC_DARK)

    default_rule = find_default_rule(rules) or DomainRule()

    overrides = default_rule.colors
    if isinstance(overrides, Mapping):
        global_overrides: dict[str, str] = {}
        light_overrides: dict[str, str] = {}
        dark_overrides: dict[str, str] = {}
        for key, value in overrides.items():
            key_lower = str(key).strip().lower()
            if key_lower == "light":
                light_overrides.update(_normalize_color_mapping(value))
            elif key_lower == "dark":
                dark_overrides.update(_normalize_color_mapping(value))
            elif key_lower == "global":
                global_overrides.update(_normalize_color_mapping(value))
            elif isinstance(value, str):
                global_overrides[key_lower] = value

        light.update(global_overrides)
        dark.update(global_overrides)
        light.update(light_overrides)
        dark.update(dark_overrides)

    priority_order: list[str] = []
    seen_priorities: set[str] = set()
    for rule in rules.values():
        for name in rule.classification.get("priority", {}):
            if name not in seen_priorities:
                seen_priorities.add(name)
                priority_order.append(name)

    return ThemePalettes(light=light, dark=dark, priority_order=priority_order)
