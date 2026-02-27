"""Centralized Dashboard Theme Module.

Single source of truth for colors, typography, Plotly layout defaults,
and CSS styling. All dashboard modules should import from here instead
of defining local color palettes.

Design Philosophy:
- Curated color palette inspired by Tailwind/Material design tokens
- Semantic coloring: each color has a clear purpose
- "Unset" severity uses a desaturated, low-opacity style so critical items pop
- Consistent Plotly chart theming via shared layout builder
"""

from typing import Any


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

    layout: dict[str, Any] = {
        "height": height,
        "margin": margin,
        "font": {
            "family": FONT_FAMILY,
            "color": "#334155",  # Slate-700
        },
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "xaxis": {
            "showgrid": show_xgrid,
            "gridcolor": "rgba(148, 163, 184, 0.18)" if show_xgrid else None,
            "zeroline": False,
        },
        "yaxis": {
            "showgrid": show_ygrid,
            "gridcolor": "rgba(148, 163, 184, 0.18)" if show_ygrid else None,
            "zeroline": False,
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
            "font": {"size": 11},
        }
    elif legend_pos == "none":
        layout["showlegend"] = False

    layout.update(overrides)
    return layout


def plotly_bar_trace_style() -> dict[str, Any]:
    """Shared trace styling for bar charts.

    Returns dict to spread into ``fig.update_traces(**result)``.
    """
    return {
        "marker_line_width": 0,
        "textposition": "inside",
        "textangle": 0,
    }


# ---------------------------------------------------------------------------
# 4. GLOBAL CSS
# ---------------------------------------------------------------------------

def get_global_css() -> str:
    """Return the full global CSS string for injection via st.markdown.

    Covers:
    - Google Fonts import (Inter)
    - Base typography (font weights, sizes)
    - Sidebar dark mode
    - Metric card enhancements
    - Navigation tab bar polish
    - Radio button (tab) styling
    """
    p = PALETTE
    return f"""
<style>
/* ===== Google Fonts ===== */
@import url('{FONT_IMPORT_URL}');

/* ===== Base Typography ===== */
html, body, [class*="css"] {{
    font-family: {FONT_FAMILY} !important;
}}

h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {{
    font-weight: 600 !important;
    letter-spacing: -0.02em;
}}

h1 {{ font-size: 1.75rem !important; }}
h2 {{ font-size: 1.35rem !important; }}
h3 {{ font-size: 1.1rem !important; }}

p, li, span, label, .stMarkdown p {{
    font-weight: 400;
}}

.stCaption, [data-testid="stCaptionContainer"] {{
    font-weight: 300 !important;
    color: {p['neutral']} !important;
}}

/* ===== Sidebar ===== */
section[data-testid="stSidebar"] {{
    border-right: 2px solid {p['border']} !important;
}}

/* Sidebar title */
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
    color: {p['primary_dark']} !important;
}}

/* Sidebar dividers */
section[data-testid="stSidebar"] hr {{
    border-color: {p['border']} !important;
}}

/* Sidebar expanders */
section[data-testid="stSidebar"] [data-testid="stExpander"] {{
    border-color: {p['border']} !important;
    border-radius: 8px !important;
}}

/* Active (primary) buttons in sidebar */
section[data-testid="stSidebar"] button[kind="primary"] {{
    background-color: {p['primary']} !important;
    border-color: {p['primary']} !important;
}}

/* ===== Metric Cards ===== */
div[data-testid="stMetric"],
div[data-testid="metric-container"] {{
    background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
    border: 1px solid {p['border']};
    padding: 18px 22px;
    border-radius: 12px;
    box-shadow: {p['shadow']} 0px 4px 12px;
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
    box-shadow: {p['shadow_hover']} 0px 8px 24px;
    border-color: {p['primary_light']};
}}

/* Metric label */
div[data-testid="stMetric"] label {{
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: {p['neutral']} !important;
}}

/* Metric value */
div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    font-weight: 700 !important;
    font-size: 1.8rem !important;
    color: #1E293B !important;
}}

/* Metric delta */
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
}}

div[data-testid="stRadio"] > div > label:hover {{
    background-color: rgba(79, 70, 229, 0.06) !important;
    border-color: rgba(79, 70, 229, 0.15) !important;
}}

div[data-testid="stRadio"] > div > label[data-checked="true"] {{
    background-color: rgba(79, 70, 229, 0.1) !important;
    border-color: {p['primary']} !important;
    color: {p['primary']} !important;
}}

/* ===== Containers / Expanders ===== */
[data-testid="stExpander"] {{
    border-radius: 10px !important;
    border: 1px solid {p['border']} !important;
}}

/* st.container(border=True) */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius: 10px !important;
    border-color: {p['border']} !important;
}}

/* ===== Plotly Charts in Dark Sidebar Context ===== */
/* Ensure charts in main area keep light text */
.main .stPlotlyChart {{
    border-radius: 8px;
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
    background: rgba(148, 163, 184, 0.3);
    border-radius: 3px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: rgba(148, 163, 184, 0.5);
}}
</style>
"""


def get_metric_card_css() -> str:
    """Return CSS specifically for metric card styling.

    This is kept for backward compatibility with components.py.
    The full styling is now in get_global_css().
    """
    return ""  # Handled by get_global_css() now
