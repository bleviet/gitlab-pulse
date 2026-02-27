"""Centralized Dashboard Theme Module.

Single source of truth for colors, typography, Plotly layout defaults,
and CSS styling. All dashboard modules should import from here instead
of defining local color palettes.

Design Philosophy:
- Curated color palette inspired by Tailwind/Material design tokens
- Semantic coloring: each color has a clear purpose
- "Unset" severity uses a desaturated, low-opacity style so critical items pop
- Consistent Plotly chart theming via shared layout builder
- Runtime theme switching: 3 light + 3 dark mood themes
"""

from typing import Any


# ---------------------------------------------------------------------------
# 0. THEME DEFINITIONS  (light × 3, dark × 3)
# ---------------------------------------------------------------------------

# Each theme is a plain dict with CSS-ready color tokens.
THEMES: dict[str, dict[str, Any]] = {
    # ── Light ───────────────────────────────────────────────────────────────
    "Cloud Dancer": {
        "icon": "☁️",
        "is_dark": False,
        # Surfaces
        "bg":            "#F0EEE9",
        "surface":       "#FFFFFF",
        "surface_hover": "#E7D8C6",
        # Text
        "text":          "#141414",
        "text_muted":    "#6B7280",
        # Accent (Signal Blue)
        "accent":        "#3B7BFF",
        "accent_light":  "rgba(59,123,255,0.10)",
        "accent_border": "rgba(59,123,255,0.35)",
        # Sidebar
        "sidebar_bg":        "#E7D8C6",
        "sidebar_surface":   "#D8C9B2",
        "sidebar_text":      "#141414",
        "sidebar_text_muted":"#6B7280",
        "sidebar_border":    "rgba(20,20,20,0.10)",
        "sidebar_accent":    "#3B7BFF",
        # Misc
        "border":       "rgba(20,20,20,0.08)",
        "shadow":       "rgba(20,20,20,0.05)",
        "shadow_hover": "rgba(20,20,20,0.12)",
        # Plotly
        "plotly_font":  "#1F2937",
        "plotly_grid":  "rgba(20,20,20,0.07)",
        # Metric card gradient
        "card_grad_a":  "#FFFFFF",
        "card_grad_b":  "#F7F3EE",
    },
    "Soft Stone": {
        "icon": "🪨",
        "is_dark": False,
        "bg":            "#F5F5F5",
        "surface":       "#FFFFFF",
        "surface_hover": "#EBEBEB",
        "text":          "#2B2F36",
        "text_muted":    "#6B7280",
        "accent":        "#00A8E8",
        "accent_light":  "rgba(0,168,232,0.10)",
        "accent_border": "rgba(0,168,232,0.35)",
        "sidebar_bg":        "#E8E8E8",
        "sidebar_surface":   "#D8D8D8",
        "sidebar_text":      "#2B2F36",
        "sidebar_text_muted":"#6B7280",
        "sidebar_border":    "rgba(43,47,54,0.10)",
        "sidebar_accent":    "#00A8E8",
        "border":       "rgba(43,47,54,0.08)",
        "shadow":       "rgba(43,47,54,0.05)",
        "shadow_hover": "rgba(43,47,54,0.12)",
        "plotly_font":  "#2B2F36",
        "plotly_grid":  "rgba(43,47,54,0.07)",
        "card_grad_a":  "#FFFFFF",
        "card_grad_b":  "#F0F0F0",
    },
    "Eco-Minimal": {
        "icon": "🌿",
        "is_dark": False,
        "bg":            "#FDF8F3",
        "surface":       "#FFFFFF",
        "surface_hover": "#EDE5DA",
        "text":          "#101417",
        "text_muted":    "#4B5563",
        "accent":        "#3D9970",
        "accent_light":  "rgba(61,153,112,0.10)",
        "accent_border": "rgba(61,153,112,0.35)",
        "sidebar_bg":        "#EDE5DA",
        "sidebar_surface":   "#DDD0C2",
        "sidebar_text":      "#101417",
        "sidebar_text_muted":"#4B5563",
        "sidebar_border":    "rgba(16,20,23,0.10)",
        "sidebar_accent":    "#3D9970",
        "border":       "rgba(16,20,23,0.08)",
        "shadow":       "rgba(16,20,23,0.05)",
        "shadow_hover": "rgba(16,20,23,0.12)",
        "plotly_font":  "#101417",
        "plotly_grid":  "rgba(16,20,23,0.07)",
        "card_grad_a":  "#FFFFFF",
        "card_grad_b":  "#F5EDE2",
    },
    # ── Dark ────────────────────────────────────────────────────────────────
    "Deep Charcoal": {
        "icon": "⬛",
        "is_dark": True,
        "bg":            "#0B0D10",
        "surface":       "#151A22",
        "surface_hover": "#1C2330",
        "text":          "#E9EEF5",
        "text_muted":    "#94A3B8",
        "accent":        "#40E0FF",
        "accent_light":  "rgba(64,224,255,0.12)",
        "accent_border": "rgba(64,224,255,0.40)",
        "sidebar_bg":        "#060709",
        "sidebar_surface":   "#0E1117",
        "sidebar_text":      "#E9EEF5",
        "sidebar_text_muted":"#64748B",
        "sidebar_border":    "rgba(64,224,255,0.10)",
        "sidebar_accent":    "#40E0FF",
        "border":       "rgba(255,255,255,0.08)",
        "shadow":       "rgba(0,0,0,0.30)",
        "shadow_hover": "rgba(0,0,0,0.50)",
        "plotly_font":  "#CBD5E1",
        "plotly_grid":  "rgba(255,255,255,0.06)",
        "card_grad_a":  "#151A22",
        "card_grad_b":  "#0F1318",
    },
    "Night Plum": {
        "icon": "🔮",
        "is_dark": True,
        "bg":            "#1A1625",
        "surface":       "#231D33",
        "surface_hover": "#2E2641",
        "text":          "#E9EEF5",
        "text_muted":    "#9CA3AF",
        "accent":        "#B9A7FF",
        "accent_light":  "rgba(185,167,255,0.12)",
        "accent_border": "rgba(185,167,255,0.40)",
        "sidebar_bg":        "#100D1A",
        "sidebar_surface":   "#1A1625",
        "sidebar_text":      "#E9EEF5",
        "sidebar_text_muted":"#6B7280",
        "sidebar_border":    "rgba(185,167,255,0.12)",
        "sidebar_accent":    "#B9A7FF",
        "border":       "rgba(255,255,255,0.08)",
        "shadow":       "rgba(0,0,0,0.35)",
        "shadow_hover": "rgba(0,0,0,0.55)",
        "plotly_font":  "#D1D5DB",
        "plotly_grid":  "rgba(255,255,255,0.06)",
        "card_grad_a":  "#231D33",
        "card_grad_b":  "#1A1625",
    },
    "Neon Minimal": {
        "icon": "⚡",
        "is_dark": True,
        "bg":            "#070A0F",
        "surface":       "#111318",
        "surface_hover": "#1A1D24",
        "text":          "#E9EEF5",
        "text_muted":    "#9CA3AF",
        "accent":        "#B6FF3B",
        "accent_light":  "rgba(182,255,59,0.10)",
        "accent_border": "rgba(182,255,59,0.40)",
        "sidebar_bg":        "#040507",
        "sidebar_surface":   "#0A0C10",
        "sidebar_text":      "#E9EEF5",
        "sidebar_text_muted":"#6B7280",
        "sidebar_border":    "rgba(182,255,59,0.10)",
        "sidebar_accent":    "#B6FF3B",
        "border":       "rgba(255,255,255,0.07)",
        "shadow":       "rgba(0,0,0,0.40)",
        "shadow_hover": "rgba(0,0,0,0.60)",
        "plotly_font":  "#D1D5DB",
        "plotly_grid":  "rgba(255,255,255,0.05)",
        "card_grad_a":  "#111318",
        "card_grad_b":  "#0A0D12",
    },
}

DEFAULT_THEME = "Cloud Dancer"


def get_active_theme() -> dict[str, Any]:
    """Return the active theme dict from session state.

    Safe to call anywhere; falls back to DEFAULT_THEME if session state
    is not yet initialised or an unknown theme name is stored.
    """
    try:
        import streamlit as st
        name = st.session_state.get("ui_theme", DEFAULT_THEME)
    except Exception:
        name = DEFAULT_THEME
    return THEMES.get(name, THEMES[DEFAULT_THEME])


# ---------------------------------------------------------------------------
# 1. TYPOGRAPHY
# ---------------------------------------------------------------------------

FONT_FAMILY = "'Inter', 'Roboto', 'Segoe UI', sans-serif"
FONT_IMPORT_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Inter:wght@300;400;500;600;700&display=swap"
)

# ---------------------------------------------------------------------------
# 2. COLOR PALETTE  (Tailwind-inspired semantic tokens)
# ---------------------------------------------------------------------------

PALETTE: dict[str, str] = {
    # Brand / UI
    "primary": "#4F46E5",       # Indigo-600
    "primary_light": "#818CF8", # Indigo-400
    "primary_dark": "#3730A3",  # Indigo-800
    "neutral": "#64748B",       # Slate-500

    # Status / Flow
    "active": "#006C3B",        # Green (matches YAML)
    "waiting": "#D62728",       # Red (matches YAML)
    "completed": "#4D217A",     # Purple (matches YAML)
    "stale": "#D62728",         # Red

    # Issue Types
    "bug": "#EF4444",           # Red-500
    "feature": "#006C3B",       # Green
    "task": "#10B981",          # Emerald-500
    "epic": "#8B5CF6",          # Violet-500

    # Severity  (modern vibrant palette — Tailwind 400-range)
    "critical": "#F43F5E",      # Rose-500   (contemporary rose-red)
    "high": "#FB923C",          # Orange-400 (warm, vivid)
    "medium": "#FBBF24",        # Amber-400  (clear, bright gold)
    "low": "#34D399",           # Emerald-400 (fresh, light green)
    "unset": "#94A3B8",         # Slate-400  (visible but still neutral)

    # Priority
    "p1": "#F43F5E",
    "p2": "#FBBF24",
    "p3": "#34D399",

    # Chart-specific
    "opened": "#6366F1",        # Indigo-500
    "closed": "#10B981",        # Emerald-500
    "scope_line": "#94A3B8",    # Slate-400

    # Burnup panels
    "burnup_feature_fill": "#166534",
    "burnup_feature_area": "#BBF7D0",
    "burnup_bug_fill": "#991B1B",
    "burnup_bug_area": "#FECACA",
    "burnup_task_fill": "#374151",
    "burnup_task_area": "#E5E7EB",

    # Milestone statuses
    "ms_complete": "#7C3AED",   # Violet-600
    "ms_incomplete": "#DC2626", # Red-600
    "ms_on_track": "#16A34A",   # Green-600
    "ms_overdue": "#EA580C",    # Orange-600
    "ms_highlight": "#F59E0B",  # Amber-500

    # Surfaces (for CSS)
    "surface": "#FFFFFF",
    "surface_hover": "#F8FAFC",
    "border": "rgba(148, 163, 184, 0.25)",
    "shadow": "rgba(15, 23, 42, 0.06)",
    "shadow_hover": "rgba(15, 23, 42, 0.12)",

    # Sidebar dark mode
    "sidebar_bg": "#1E293B",       # Slate-800
    "sidebar_bg_alt": "#0F172A",   # Slate-900
    "sidebar_text": "#E2E8F0",     # Slate-200
    "sidebar_text_muted": "#94A3B8",  # Slate-400
    "sidebar_border": "rgba(148, 163, 184, 0.15)",
    "sidebar_accent": "#818CF8",   # Indigo-400
}

# Convenience aliases used by chart widgets
SEVERITY_COLORS: dict[str, str] = {
    "Critical": PALETTE["critical"],
    "High": PALETTE["high"],
    "Medium": PALETTE["medium"],
    "Low": PALETTE["low"],
    "Unset": PALETTE["unset"],
}

ISSUE_TYPE_COLORS: dict[str, str] = {
    "Bug": PALETTE["bug"],
    "Feature": PALETTE["feature"],
    "Task": PALETTE["task"],
    "Epic": PALETTE["epic"],
}

STAGE_TYPE_COLORS: dict[str, str] = {
    "active": PALETTE["active"],
    "waiting": PALETTE["waiting"],
    "completed": PALETTE["completed"],
    "backlog": PALETTE["neutral"],
    "triage": PALETTE["neutral"],
}


# ---------------------------------------------------------------------------
# 3. PLOTLY LAYOUT DEFAULTS
# ---------------------------------------------------------------------------

def plotly_layout(
    height: int = 400,
    margin: dict[str, int] | None = None,
    show_xgrid: bool = False,
    show_ygrid: bool = True,
    legend_pos: str = "top",
    **overrides: Any,
) -> dict[str, Any]:
    """Build a consistent Plotly layout dict.

    Args:
        height: Chart height in px.
        margin: Custom margin dict. Defaults to compact margins.
        show_xgrid: Whether to show vertical grid lines.
        show_ygrid: Whether to show horizontal grid lines.
        legend_pos: "top" (horizontal above chart) or "none".
        **overrides: Any extra keys merged into the layout dict.

    Returns:
        Dict suitable for ``fig.update_layout(**result)``.
    """
    if margin is None:
        margin = {"l": 0, "r": 20, "t": 10, "b": 0}

    t = get_active_theme()
    font_color = t["plotly_font"]
    grid_color = t["plotly_grid"]

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
        # Any other legend position: still enforce font color
        layout.setdefault("legend", {})["font"] = {"color": font_color}

    layout.update(overrides)
    return layout


def plotly_bar_trace_style() -> dict[str, Any]:
    """Shared trace styling for bar charts.

    Returns dict to spread into ``fig.update_traces(**result)``.
    Theme-aware: forces text labels to use the active theme's font color.
    """
    t = get_active_theme()
    return {
        "marker_line_width": 0,
        "textposition": "inside",
        "textangle": 0,
        "textfont": {"color": t["plotly_font"]},
    }


# ---------------------------------------------------------------------------
# 4. GLOBAL CSS
# ---------------------------------------------------------------------------

def get_global_css() -> str:
    """Return the full global CSS string for injection via st.markdown.

    Theme-aware: reads the active theme from session state on every render
    so switching themes is reflected instantly without a full page reload.

    Covers:
    - Google Fonts import (Inter)
    - Base typography (font weights, sizes)
    - App + sidebar background & text via active theme
    - Metric card enhancements (dark/light adaptive)
    - Navigation tab bar polish
    - Radio button (tab) styling driven by accent color
    - Expander / container borders
    - Scrollbar
    """
    t = get_active_theme()
    p = PALETTE

    # Accent color shorthand for CSS expressions
    accent          = t["accent"]
    accent_light    = t["accent_light"]
    accent_border   = t["accent_border"]
    bg              = t["bg"]
    surface         = t["surface"]
    text            = t["text"]
    text_muted      = t["text_muted"]
    border          = t["border"]
    shadow          = t["shadow"]
    shadow_hover    = t["shadow_hover"]
    card_grad_a     = t["card_grad_a"]
    card_grad_b     = t["card_grad_b"]
    metric_val_color = t["text"]
    # Sidebar tokens
    sb_bg    = t["sidebar_bg"]
    sb_surf  = t["sidebar_surface"]
    sb_text  = t["sidebar_text"]
    sb_muted = t["sidebar_text_muted"]
    sb_bdr   = t["sidebar_border"]
    sb_acc   = t["sidebar_accent"]
    # Dark-mode extras
    color_scheme = "dark" if t["is_dark"] else "light"

    return f"""
<style>
/* ===== Google Fonts ===== */
@import url('{FONT_IMPORT_URL}');

/* ===== Color Scheme ===== */
:root {{
    color-scheme: {color_scheme};
}}

/* ===== App Background ===== */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"] {{
    background-color: {bg} !important;
}}

/* ===== Base Typography ===== */
html, body, [class*="css"] {{
    font-family: {FONT_FAMILY} !important;
    color: {text};
}}

h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
    font-weight: 600 !important;
    letter-spacing: -0.02em;
    color: {text} !important;
}}

h1 {{ font-size: 1.75rem !important; }}
h2 {{ font-size: 1.35rem !important; }}
h3 {{ font-size: 1.1rem !important; }}

p, li, span, .stMarkdown p {{
    font-weight: 400;
    color: {text};
}}

label {{
    color: {text_muted} !important;
}}

.stCaption, [data-testid="stCaptionContainer"] {{
    font-weight: 300 !important;
    color: {text_muted} !important;
}}

/* ===== Sidebar ===== */
section[data-testid="stSidebar"] {{
    background-color: {sb_bg} !important;
    border-right: 1px solid {sb_bdr} !important;
}}

section[data-testid="stSidebar"] > div {{
    background-color: {sb_bg} !important;
}}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
    color: {sb_text} !important;
}}

section[data-testid="stSidebar"] p,
section[data-testid="stSidebar"] span,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stMarkdown {{
    color: {sb_text} !important;
}}

section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{
    color: {sb_muted} !important;
}}

section[data-testid="stSidebar"] hr {{
    border-color: {sb_bdr} !important;
}}

section[data-testid="stSidebar"] [data-testid="stExpander"] {{
    background-color: {sb_surf} !important;
    border-color: {sb_bdr} !important;
    border-radius: 8px !important;
}}

section[data-testid="stSidebar"] button[kind="primary"] {{
    background-color: {sb_acc} !important;
    border-color: {sb_acc} !important;
    color: {bg} !important;
}}

/* ===== Metric Cards ===== */
div[data-testid="stMetric"],
div[data-testid="metric-container"] {{
    background: linear-gradient(135deg, {card_grad_a} 0%, {card_grad_b} 100%);
    border: 1px solid {border};
    padding: 18px 22px;
    border-radius: 12px;
    box-shadow: {shadow} 0px 4px 12px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    min-height: 140px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    position: relative;
    overflow: hidden;
}}

div[data-testid="stMetric"]:hover {{
    transform: translateY(-3px);
    box-shadow: {shadow_hover} 0px 8px 24px;
    border-color: {accent_border};
}}

div[data-testid="stMetric"] label {{
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: {text_muted} !important;
}}

div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    font-weight: 700 !important;
    font-size: 1.8rem !important;
    color: {metric_val_color} !important;
}}

div[data-testid="stMetric"] [data-testid="stMetricDelta"] {{
    font-weight: 400;
    font-size: 0.8rem !important;
}}

/* ===== Navigation Radio Tabs ===== */
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
    color: {text} !important;
}}

div[data-testid="stRadio"] > div > label:hover {{
    background-color: {accent_light} !important;
    border-color: {accent_border} !important;
}}

div[data-testid="stRadio"] > div > label[data-checked="true"] {{
    background-color: {accent_light} !important;
    border-color: {accent} !important;
    color: {accent} !important;
}}

/* ===== Containers / Expanders ===== */
[data-testid="stExpander"] {{
    border-radius: 10px !important;
    border: 1px solid {border} !important;
    background-color: {surface} !important;
}}

[data-testid="stExpander"] summary {{
    color: {text} !important;
}}

div[data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius: 10px !important;
    border-color: {border} !important;
    background-color: {surface} !important;
}}

/* ===== Main content blocks ===== */
[data-testid="stVerticalBlock"] {{
    background-color: transparent;
}}

/* ===== Plotly Charts ===== */
.main .stPlotlyChart {{
    border-radius: 8px;
}}

/* ===== Selectbox / Input fields ===== */
[data-testid="stSelectbox"] > div,
[data-testid="stTextInput"] > div > div {{
    background-color: {surface} !important;
    color: {text} !important;
    border-color: {border} !important;
}}

/* ===== Scrollbar ===== */
::-webkit-scrollbar {{
    width: 6px;
    height: 6px;
}}
::-webkit-scrollbar-track {{
    background: transparent;
}}
::-webkit-scrollbar-thumb {{
    background: {border};
    border-radius: 3px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: {accent_border};
}}
</style>
"""


def get_metric_card_css() -> str:
    """Return CSS specifically for metric card styling.

    This is kept for backward compatibility with components.py.
    The full styling is now in get_global_css().
    """
    return ""  # Handled by get_global_css() now
