"""Centralized Dashboard Theme Module.

This module now follows Streamlit's official theming model via
`.streamlit/config.toml` (`[theme]`, `[theme.light]`, `[theme.dark]`).

Only non-native visual polish remains in injected CSS (metric cards,
radio-tab presentation, and custom scrollbar).
"""

from __future__ import annotations

import collections.abc
import re
from typing import Any

FONT_FAMILY = "'SpaceGrotesk', 'Poppins', sans-serif"
FONT_IMPORT_URL = ""


def _parse_rgb_from_color(value: str) -> tuple[int, int, int] | None:
    if not value:
        return None

    color = value.strip().lower()
    if color.startswith("#"):
        hex_value = color.lstrip("#")
        if len(hex_value) == 3:
            hex_value = "".join(ch * 2 for ch in hex_value)
        if len(hex_value) != 6:
            return None
        return (
            int(hex_value[0:2], 16),
            int(hex_value[2:4], 16),
            int(hex_value[4:6], 16),
        )

    rgb_match = re.match(r"rgba?\((\d+)\s*,\s*(\d+)\s*,\s*(\d+)", color)
    if rgb_match:
        return tuple(int(rgb_match.group(i)) for i in range(1, 4))

    return None


def _is_dark_color(value: str) -> bool:
    rgb = _parse_rgb_from_color(value)
    if rgb is None:
        return False
    red, green, blue = rgb
    luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255.0
    return luminance < 0.5


def get_active_theme_mode() -> str:
    """Return active Streamlit mode: ``"light"`` or ``"dark"``.

    Mode detection is based on resolved ``theme.backgroundColor`` from the
    currently active Streamlit theme.
    """
    try:
        import streamlit as st

        bg = str(st.get_option("theme.backgroundColor") or "")
        return "dark" if _is_dark_color(bg) else "light"
    except Exception:
        return "light"


class ThemeAwareDict(collections.abc.MutableMapping):
    """A dictionary wrapper that dynamically swaps light/dark palettes
    based on the currently active Streamlit theme mode.
    """

    def __init__(self, light_dict: dict[str, str], dark_dict: dict[str, str]):
        self.light_dict = light_dict
        self.dark_dict = dark_dict

    def _get_active_dict(self) -> dict[str, str]:
        mode = get_active_theme_mode()
        return self.dark_dict if mode == "dark" else self.light_dict

    def __getitem__(self, key: str) -> str:
        return self._get_active_dict()[key]

    def __setitem__(self, key: str, value: str) -> None:
        self.light_dict[key] = value
        self.dark_dict[key] = value

    def __delitem__(self, key: str) -> None:
        del self.light_dict[key]
        del self.dark_dict[key]

    def __iter__(self):
        return iter(self._get_active_dict())

    def __len__(self) -> int:
        return len(self._get_active_dict())

    def copy(self) -> dict[str, str]:
        """Return a deep copy of the active dictionary (not a ThemeAwareDict)."""
        return self._get_active_dict().copy()


_PALETTE_LIGHT: dict[str, str] = {
    "primary": "#4F46E5",
    "primary_light": "#818CF8",
    "primary_dark": "#3730A3",
    "neutral": "#64748B",
    "active": "#006C3B",
    "waiting": "#D62728",
    "completed": "#4D217A",
    "stale": "#D62728",
    "bug": "#EF4444",
    "feature": "#006C3B",
    "task": "#10B981",
    "epic": "#8B5CF6",
    "critical": "#F43F5E",
    "high": "#FB923C",
    "medium": "#FBBF24",
    "low": "#34D399",
    "unset": "#94A3B8",
    "p1": "#F43F5E",
    "p2": "#FBBF24",
    "p3": "#34D399",
    "opened": "#6366F1",
    "closed": "#10B981",
    "scope_line": "#94A3B8",
    "burnup_feature_fill": "#166534",
    "burnup_feature_area": "#BBF7D0",
    "burnup_bug_fill": "#991B1B",
    "burnup_bug_area": "#FECACA",
    "burnup_task_fill": "#374151",
    "burnup_task_area": "#E5E7EB",
    "ms_complete": "#7C3AED",
    "ms_incomplete": "#DC2626",
    "ms_on_track": "#16A34A",
    "ms_overdue": "#EA580C",
    "ms_highlight": "#F59E0B",
    "surface": "#FFFFFF",
    "surface_hover": "#F8FAFC",
    "border": "rgba(148, 163, 184, 0.25)",
    "shadow": "rgba(15, 23, 42, 0.06)",
    "shadow_hover": "rgba(15, 23, 42, 0.12)",
    "sidebar_bg": "#1E293B",
    "sidebar_bg_alt": "#0F172A",
    "sidebar_text": "#E2E8F0",
    "sidebar_text_muted": "#94A3B8",
    "sidebar_border": "rgba(148, 163, 184, 0.15)",
    "sidebar_accent": "#818CF8",
}

_PALETTE_DARK: dict[str, str] = {
    "primary": "#4F46E5",
    "primary_light": "#818CF8",
    "primary_dark": "#3730A3",
    "neutral": "#64748B",
    "active": "#1ed760",
    "waiting": "#cb785c",
    "completed": "#4D217A",
    "stale": "#D62728",
    "bug": "#EF4444",
    "feature": "#1ed760",
    "task": "#10B981",
    "epic": "#8B5CF6",
    "critical": "#cb785c",
    "high": "#FB923C",
    "medium": "#FBBF24",
    "low": "#34D399",
    "unset": "#94A3B8",
    "p1": "#cb785c",
    "p2": "#FBBF24",
    "p3": "#34D399",
    "opened": "#6366F1",
    "closed": "#10B981",
    "scope_line": "#94A3B8",
    "burnup_feature_fill": "#166534",
    "burnup_feature_area": "#BBF7D0",
    "burnup_bug_fill": "#991B1B",
    "burnup_bug_area": "#FECACA",
    "burnup_task_fill": "#374151",
    "burnup_task_area": "#E5E7EB",
    "ms_complete": "#7C3AED",
    "ms_incomplete": "#DC2626",
    "ms_on_track": "#16A34A",
    "ms_overdue": "#EA580C",
    "ms_highlight": "#F59E0B",
    "surface": "#121212",
    "surface_hover": "#2a2a2a",
    "border": "rgba(124, 124, 124, 0.3)",
    "shadow": "rgba(0, 0, 0, 0.5)",
    "shadow_hover": "rgba(0, 0, 0, 0.8)",
    "sidebar_bg": "#121212",
    "sidebar_bg_alt": "#000000",
    "sidebar_text": "#ffffff",
    "sidebar_text_muted": "#b3b3b3",
    "sidebar_border": "rgba(124, 124, 124, 0.15)",
    "sidebar_accent": "#1ed760",
}

# The wrapper dictionary that returns the active mode colors dynamically
PALETTE = ThemeAwareDict(_PALETTE_LIGHT, _PALETTE_DARK)

SEVERITY_COLORS = ThemeAwareDict(
    {
        "Critical": _PALETTE_LIGHT["critical"],
        "High": _PALETTE_LIGHT["high"],
        "Medium": _PALETTE_LIGHT["medium"],
        "Low": _PALETTE_LIGHT["low"],
        "Unset": _PALETTE_LIGHT["unset"],
    },
    {
        "Critical": _PALETTE_DARK["critical"],
        "High": _PALETTE_DARK["high"],
        "Medium": _PALETTE_DARK["medium"],
        "Low": _PALETTE_DARK["low"],
        "Unset": _PALETTE_DARK["unset"],
    },
)

ISSUE_TYPE_COLORS = ThemeAwareDict(
    {
        "Bug": _PALETTE_LIGHT["bug"],
        "Feature": _PALETTE_LIGHT["feature"],
        "Task": _PALETTE_LIGHT["task"],
        "Epic": _PALETTE_LIGHT["epic"],
    },
    {
        "Bug": _PALETTE_DARK["bug"],
        "Feature": _PALETTE_DARK["feature"],
        "Task": _PALETTE_DARK["task"],
        "Epic": _PALETTE_DARK["epic"],
    },
)

STAGE_TYPE_COLORS = ThemeAwareDict(
    {
        "active": _PALETTE_LIGHT["active"],
        "waiting": _PALETTE_LIGHT["waiting"],
        "completed": _PALETTE_LIGHT["completed"],
        "backlog": _PALETTE_LIGHT["neutral"],
        "triage": _PALETTE_LIGHT["neutral"],
    },
    {
        "active": _PALETTE_DARK["active"],
        "waiting": _PALETTE_DARK["waiting"],
        "completed": _PALETTE_DARK["completed"],
        "backlog": _PALETTE_DARK["neutral"],
        "triage": _PALETTE_DARK["neutral"],
    },
)


_THEME_MODE_TOKENS: dict[str, dict[str, str]] = {
    "light": {
        "accent": "#cb785c",
        "accent_light": "rgba(203,120,92,0.15)",
        "accent_border": "rgba(203,120,92,0.40)",
        "text": "#3d3a2a",
        "text_muted": "#6b695e",
        "border": "#d3d2ca",
        "plotly_font": "#3d3a2a",
        "plotly_grid": "rgba(211,210,202,0.50)",
        "card_grad_a": "#fdfdf8",
        "card_grad_b": "#f0f0ec",
        "shadow": "rgba(61,58,42,0.05)",
        "shadow_hover": "rgba(61,58,42,0.12)",
    },
    "dark": {
        "accent": "#1ed760",
        "accent_light": "rgba(30,215,96,0.15)",
        "accent_border": "rgba(30,215,96,0.40)",
        "text": "#ffffff",
        "text_muted": "#b3b3b3",
        "border": "#7c7c7c",
        "plotly_font": "#ffffff",
        "plotly_grid": "rgba(124,124,124,0.30)",
        "card_grad_a": "#2a2a2a",
        "card_grad_b": "#121212",
        "shadow": "rgba(0,0,0,0.50)",
        "shadow_hover": "rgba(0,0,0,0.80)",
    },
}


def get_active_theme() -> dict[str, Any]:
    """Backward-compatible theme payload for existing callers."""
    mode = get_active_theme_mode()
    payload = dict(_THEME_MODE_TOKENS[mode])
    payload["is_dark"] = mode == "dark"
    return payload


def get_streamlit_theme_color(option_name: str, fallback: str) -> str:
    """Return a resolved Streamlit theme color option with fallback.

    Args:
        option_name: Theme option name without ``theme.`` prefix
            (e.g. ``"textColor"``, ``"primaryColor"``).
        fallback: Value to use when option is unavailable.
    """
    try:
        import streamlit as st

        value = st.get_option(f"theme.{option_name}")
        if isinstance(value, str) and value.strip():
            return value
    except Exception:
        pass
    return fallback


def _with_alpha(color: str, alpha: float, fallback: str) -> str:
    rgb = _parse_rgb_from_color(color)
    if rgb is None:
        return fallback
    red, green, blue = rgb
    return f"rgba({red},{green},{blue},{alpha})"


def get_plotly_font_color() -> str:
    """Return a Plotly-valid font color derived from Streamlit theme."""
    mode = get_active_theme_mode()
    return get_streamlit_theme_color(
        "textColor", _THEME_MODE_TOKENS[mode]["plotly_font"]
    )


def get_plotly_grid_color() -> str:
    """Return Plotly grid color derived from active Streamlit theme."""
    mode = get_active_theme_mode()
    border_color = get_streamlit_theme_color(
        "borderColor", _THEME_MODE_TOKENS[mode]["border"]
    )
    return _with_alpha(
        border_color, alpha=0.22, fallback=_THEME_MODE_TOKENS[mode]["plotly_grid"]
    )


def plotly_layout(
    height: int = 400,
    margin: dict[str, int] | None = None,
    show_xgrid: bool = False,
    show_ygrid: bool = True,
    legend_pos: str = "top",
    **overrides: Any,
) -> dict[str, Any]:
    """Build a consistent Plotly layout dictionary."""
    if margin is None:
        margin = {"l": 0, "r": 20, "t": 10, "b": 0}

    font_color = get_plotly_font_color()
    grid_color = get_plotly_grid_color()

    layout: dict[str, Any] = {
        "height": height,
        "margin": margin,
        "font": {
            "family": FONT_FAMILY,
            "color": font_color,
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "xaxis": {
            "showgrid": show_xgrid,
            "gridcolor": grid_color if show_xgrid else None,
            "zeroline": False,
            "color": font_color,
            "tickfont": {"color": font_color},
            "title": {"font": {"color": font_color}},
        },
        "yaxis": {
            "showgrid": show_ygrid,
            "gridcolor": grid_color if show_ygrid else None,
            "zeroline": False,
            "color": font_color,
            "tickfont": {"color": font_color},
            "title": {"font": {"color": font_color}},
        },
    }

    if legend_pos == "top":
        layout["legend"] = {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
            "title": None,
            "font": {"size": 11, "color": font_color},
        }
    elif legend_pos == "none":
        layout["showlegend"] = False
    else:
        layout.setdefault("legend", {})["font"] = {"color": font_color}

    layout.update(overrides)
    return layout


def plotly_bar_trace_style() -> dict[str, Any]:
    """Return shared trace styling for bar charts."""
    return {
        "marker_line_width": 0,
        "textposition": "inside",
        "textangle": 0,
        "textfont": {"color": get_plotly_font_color()},
    }


def get_global_css() -> str:
    """Return minimal CSS not covered by Streamlit config theming."""
    token = _THEME_MODE_TOKENS[get_active_theme_mode()]

    return f"""
<style>
/* Metric cards */
div[data-testid="stMetric"],
div[data-testid="metric-container"] {{
    background: linear-gradient(135deg, {token['card_grad_a']} 0%, {token['card_grad_b']} 100%);
    border: 1px solid {token['border']};
    padding: 18px 22px;
    border-radius: 12px;
    box-shadow: {token['shadow']} 0 4px 12px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    min-height: 140px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    overflow: hidden;
}}

div[data-testid="stMetric"]:hover {{
    transform: translateY(-3px);
    box-shadow: {token['shadow_hover']} 0 8px 24px;
    border-color: {token['accent_border']};
}}

div[data-testid="stMetric"] label {{
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: {token['text_muted']} !important;
}}

div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    font-weight: 700 !important;
    font-size: 1.8rem !important;
    color: {token['text']} !important;
}}

div[data-testid="stMetric"] [data-testid="stMetricDelta"] {{
    font-weight: 400;
    font-size: 0.8rem !important;
}}

/* Radio rendered as tabs */
div[data-testid="stRadio"] > div {{
    gap: 2px !important;
}}

div[data-testid="stRadio"] > div > label {{
    padding: 8px 16px !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s ease !important;
    border: 1px solid transparent !important;
    color: {token['text']} !important;
}}

div[data-testid="stRadio"] > div > label:hover {{
    background-color: {token['accent_light']} !important;
    border-color: {token['accent_border']} !important;
}}

div[data-testid="stRadio"] > div > label[data-checked="true"] {{
    background-color: {token['accent_light']} !important;
    border-color: {token['accent']} !important;
    color: {token['accent']} !important;
}}

/* Plotly wrapper */
.main .stPlotlyChart {{
    border-radius: 8px;
}}

/* Scrollbar */
::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
}}
::-webkit-scrollbar-track {{
    background: transparent;
}}
::-webkit-scrollbar-thumb {{
    background: {token['border']};
    border-radius: 3px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: {token['accent_border']};
}}
</style>
"""
