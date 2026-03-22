"""Centralized Dashboard Theme Module.

UI chrome colors (backgroundColor, textColor, borderColor) are owned by
Streamlit's native theming config in`.streamlit/config.toml`. 

This module provides:
  - Semantic domain color palettes (issue types, severities, stages)
  - Plotly layout helpers that adapt to the active Streamlit theme
  - Minimal CSS injection for custom visual components (metric cards, etc.)
  - Rule-based color overrides loaded from YAML configuration
"""

from __future__ import annotations

import collections.abc
import re
from typing import Any

# --- Font Constants ---
FONT_BODY    = "'Manrope', sans-serif"
FONT_HEADING = "'Space Grotesk', 'SpaceGrotesk', sans-serif"
FONT_CODE    = "'Space Mono', 'SpaceMono', monospace"

_GOOGLE_FONTS_URL = (
    "https://fonts.googleapis.com/css2?"
    "family=Manrope:wght@400;500;600;700;800"
    "&family=Space+Grotesk:wght@400;500;600;700"
    "&display=swap"
)

# --- Color Parsing Utilities ---

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


def _with_alpha(color: str, alpha: float, fallback: str) -> str:
    rgb = _parse_rgb_from_color(color)
    if rgb is None:
        return fallback
    red, green, blue = rgb
    return f"rgba({red},{green},{blue},{alpha})"


# --- Mode Detection ---

def get_active_theme_mode() -> str:
    """Return active Streamlit mode: ``"light"`` or ``"dark"``.

    Uses ``st.context.theme`` (dict-like) which reflects the client's active
    theme selection, unlike ``st.get_option()`` which returns server-side config.
    """
    try:
        import streamlit as st
        return str(st.context.theme.get("type", "dark"))
    except Exception:
        return "dark"


def get_streamlit_theme_color(option_name: str, fallback: str) -> str:
    """Return a resolved Streamlit theme color from the active client theme.

    Reads from ``st.context.theme`` (dict-like) which reflects the resolved
    theme the client is actually using (respects light/dark toggle).
    """
    try:
        import streamlit as st
        value = st.context.theme.get(option_name)
        if isinstance(value, str) and value.strip():
            return value
    except Exception:
        pass
    return fallback


# --- Semantic Domain Palettes ---

_SEMANTIC_LIGHT: dict[str, str] = {
    # Issue Types — mapped to frontend-design chart palette (light)
    "bug": "#b51c3c",       # --chart-4 Rose
    "feature": "#1a7a62",   # --chart-7 Mint
    "task": "#005e9e",      # --chart-1 Cyan
    "epic": "#8a0ea8",      # --chart-3 Orchid

    # Status/Flow Stages
    "active": "#1a7a62",    # --chart-7 Mint
    "waiting": "#b06000",   # --chart-6 Amber
    "completed": "#8a0ea8", # --chart-3 Orchid
    "stale": "#b51c3c",     # --chart-4 Rose
    "opened": "#005e9e",    # --chart-1 Cyan
    "closed": "#1a7a62",    # --chart-7 Mint

    # UI/Domain Shared
    "primary": "#ff512f",   # --brand
    "neutral": "#3d5370",   # --muted light

    # Severity — semantic red→orange→amber→green scale (not chart-indexed)
    "critical": "#F43F5E",
    "high": "#FB923C",
    "medium": "#FBBF24",
    "low": "#1a7a62",       # --chart-7 Mint
    "unset": "#3d5370",     # --muted light

    # Priority
    "p1": "#b51c3c",        # --chart-4 Rose
    "p2": "#b06000",        # --chart-6 Amber
    "p3": "#1a7a62",        # --chart-7 Mint

    # Chart Series specific
    "scope_line": "#3d5370",          # --muted light
    "burnup_feature_fill": "#166534",
    "burnup_feature_area": "#BBF7D0",
    "burnup_bug_fill": "#991B1B",
    "burnup_bug_area": "#FECACA",
    "burnup_task_fill": "#374151",
    "burnup_task_area": "#E5E7EB",
    "ms_complete": "#006ea3",         # --accent light
    "ms_incomplete": "#b51c3c",       # --chart-4 Rose
    "ms_on_track": "#1a7a62",         # --chart-7 Mint
    "ms_overdue": "#ff512f",          # --brand
    "ms_highlight": "#b06000",        # --chart-6 Amber

    # Grid details (zebra stripes etc.)
    "surface_hover": "#dce3f0",
}

_SEMANTIC_DARK: dict[str, str] = {
    # Issue Types — mapped to frontend-design chart palette (dark)
    "bug": "#f5576c",       # --chart-4 Rose
    "feature": "#56d4b0",   # --chart-7 Mint
    "task": "#4facfe",      # --chart-1 Cyan
    "epic": "#c76bff",      # --chart-3 Orchid

    # Status/Flow Stages
    "active": "#56d4b0",    # --chart-7 Mint
    "waiting": "#f4a44a",   # --chart-6 Amber
    "completed": "#c76bff", # --chart-3 Orchid
    "stale": "#f5576c",     # --chart-4 Rose
    "opened": "#4facfe",    # --chart-1 Cyan
    "closed": "#56d4b0",    # --chart-7 Mint

    # UI/Domain Shared
    "primary": "#ff512f",   # --brand
    "neutral": "#7a8fa8",   # --muted dark

    # Severity — semantic red→orange→amber→green scale (not chart-indexed)
    "critical": "#e06565",
    "high": "#e88236",
    "medium": "#f4a44a",    # --chart-6 Amber (natural fit for medium)
    "low": "#56d4b0",       # --chart-7 Mint
    "unset": "#7a8fa8",     # --muted dark

    # Priority
    "p1": "#dd2476",        # --brand-2 (kept — reserved brand color)
    "p2": "#f4a44a",        # --chart-6 Amber
    "p3": "#56d4b0",        # --chart-7 Mint

    # Chart Series specific
    "scope_line": "#7a8fa8",          # --muted dark
    "burnup_feature_fill": "#166534",
    "burnup_feature_area": "#a2e8bc",
    "burnup_bug_fill": "#991b1b",
    "burnup_bug_area": "#f5b0b0",
    "burnup_task_fill": "#0c1123",    # --bg-card
    "burnup_task_area": "#4facfe",    # --chart-1 Cyan
    "ms_complete": "#00f2fe",         # --accent dark
    "ms_incomplete": "#f5576c",       # --chart-4 Rose
    "ms_on_track": "#56d4b0",         # --chart-7 Mint
    "ms_overdue": "#ff512f",          # --brand
    "ms_highlight": "#f4a44a",        # --chart-6 Amber

    # Grid details (zebra stripes etc.)
    "surface_hover": "#121c35",
}

def get_palette() -> dict[str, str]:
    """Return the active semantic palette mapping.
    
    This is the single source of truth for semantic colors in charts and widgets.
    """
    mode = get_active_theme_mode()
    return _SEMANTIC_DARK.copy() if mode == "dark" else _SEMANTIC_LIGHT.copy()

def get_severity_colors() -> dict[str, str]:
    """Return colors mapping for severities."""
    p = get_palette()
    return {
        "Critical": p["critical"],
        "High": p["high"],
        "Medium": p["medium"],
        "Low": p["low"],
        "Unset": p["unset"],
    }

def get_issue_type_colors() -> dict[str, str]:
    """Return colors mapping for issue types."""
    p = get_palette()
    return {
        "Bug": p["bug"],
        "Feature": p["feature"],
        "Task": p["task"],
        "Epic": p["epic"],
    }

def get_stage_colors() -> dict[str, str]:
    """Return colors mapping for workflow stages."""
    p = get_palette()
    return {
        "active": p["active"],
        "waiting": p["waiting"],
        "completed": p["completed"],
        "backlog": p["neutral"],
        "triage": p["neutral"],
    }

def with_alpha(color: str, alpha: float) -> str:
    """Return *color* as ``rgba(r,g,b,alpha)``.

    Accepts any hex or rgb/rgba string. Falls back to the original value if
    the color cannot be parsed.
    """
    return _with_alpha(color, alpha, color)

def get_alert_background_colors() -> dict[str, str]:
    """Return CSS ``background-color`` strings for error / warning / info rows.

    Colors are derived from the active semantic palette so they adapt to both
    light and dark mode automatically.
    """
    p = get_palette()
    mode = get_active_theme_mode()
    alpha = 0.18 if mode == "dark" else 0.14
    return {
        "error":   f"background-color: {_with_alpha(p['bug'],     alpha, 'rgba(239,68,68,0.15)')}",
        "warning": f"background-color: {_with_alpha(p['high'],    alpha, 'rgba(245,158,11,0.15)')}",
        "info":    f"background-color: {_with_alpha(p['neutral'], 0.10,  'rgba(100,116,139,0.10)')}",
    }

# --- YAML Color Overrides ---

def _normalize_color_mapping(value: Any) -> dict[str, str]:
    if not isinstance(value, collections.abc.Mapping):
        return {}
    return {str(k): str(v) for k, v in value.items() if isinstance(v, str)}

def apply_rule_color_overrides(overrides: dict[str, Any] | None) -> None:
    """Apply YAML color overrides mutatively to the semantic palettes.
    
    This should be called once at startup when rule configuration is loaded.
    """
    if not isinstance(overrides, collections.abc.Mapping):
        return

    global_overrides: dict[str, str] = {}
    light_overrides: dict[str, str] = {}
    dark_overrides: dict[str, str] = {}

    for key, value in overrides.items():
        key_lower = str(key).strip().lower()

        if key_lower == "light":
            light_overrides.update(_normalize_color_mapping(value))
            continue
        if key_lower == "dark":
            dark_overrides.update(_normalize_color_mapping(value))
            continue
        if key_lower == "global":
            global_overrides.update(_normalize_color_mapping(value))
            continue

        if isinstance(value, str):
            global_overrides[str(key)] = value

    if global_overrides:
        _SEMANTIC_LIGHT.update(global_overrides)
        _SEMANTIC_DARK.update(global_overrides)
    if light_overrides:
        _SEMANTIC_LIGHT.update(light_overrides)
    if dark_overrides:
        _SEMANTIC_DARK.update(dark_overrides)


# --- Plotly Helpers ---

def get_plotly_font_color() -> str:
    """Return a Plotly-valid font color derived from Streamlit theme."""
    mode = get_active_theme_mode()
    fallback = "#ffffff" if mode == "dark" else "#0d1120"
    return get_streamlit_theme_color("textColor", fallback)

def get_plotly_grid_color() -> str:
    """Return Plotly grid color derived from active Streamlit theme."""
    mode = get_active_theme_mode()
    fallback_border = "#1c2030" if mode == "dark" else "#c8cbd3"
    fallback_grid = "rgba(28,32,48,0.30)" if mode == "dark" else "rgba(200,203,211,0.50)"

    border_color = get_streamlit_theme_color("borderColor", fallback_border)
    return _with_alpha(border_color, alpha=0.22, fallback=fallback_grid)

def plotly_layout(
    height: int = 400,
    margin: dict[str, int] | None = None,
    show_xgrid: bool = False,
    show_ygrid: bool = True,
    legend_pos: str = "top",
    **overrides: Any,
) -> dict[str, Any]:
    """Build a consistent Plotly layout dictionary that adapts to Streamlit theme."""
    if margin is None:
        margin = {"l": 0, "r": 20, "t": 10, "b": 0}

    font_color = get_plotly_font_color()
    grid_color = get_plotly_grid_color()
    font_family = FONT_BODY

    layout: dict[str, Any] = {
        "height": height,
        "margin": margin,
        "font": {
            "family": font_family,
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


# --- CSS Injection ---

def get_global_css() -> str:
    """Return minimal CSS not covered by Streamlit config theming.
    
    Dynamically reads colors from Streamlit's base theme options to build
    custom widgets like metric cards and tabbed radios.
    """
    mode = get_active_theme_mode()

    # Read from the active client theme (respects light/dark toggle)
    bg = get_streamlit_theme_color("backgroundColor", "#050811" if mode == "dark" else "#e8ecf5")
    secondary_bg = get_streamlit_theme_color("secondaryBackgroundColor", "#0c1123" if mode == "dark" else "#f1f4fb")
    text_color = get_streamlit_theme_color("textColor", "#d4deee" if mode == "dark" else "#0d1120")
    primary = get_streamlit_theme_color("primaryColor", "#ff512f" if mode == "dark" else "#ff512f")
    border = get_streamlit_theme_color("borderColor", "#1c2030" if mode == "dark" else "#c8cbd3")

    text_muted = _with_alpha(text_color, 0.7, "#8a9bb2" if mode == "dark" else "#5a6a82")
    primary_light = _with_alpha(primary, 0.15, "transparent")
    primary_border = _with_alpha(primary, 0.40, primary)
    shadow = "rgba(0,0,0,0.50)" if mode == "dark" else "rgba(0,0,0,0.08)"
    shadow_hover = "rgba(0,0,0,0.80)" if mode == "dark" else "rgba(0,0,0,0.15)"

    # Frontend-design chart palette (8 series)
    if mode == "dark":
        chart_vars = """
    --chart-1: #4facfe;  /* Cyan   */
    --chart-2: #ff7354;  /* Coral  */
    --chart-3: #c76bff;  /* Orchid */
    --chart-4: #f5576c;  /* Rose   */
    --chart-5: #74c7f0;  /* Sky    */
    --chart-6: #f4a44a;  /* Amber  */
    --chart-7: #56d4b0;  /* Mint   */
    --chart-8: #9f7bea;  /* Mauve  */
    --chart-bg:          var(--bg-card, {secondary_bg});
    --chart-grid:        rgba(255,255,255,0.06);
    --chart-axis:        rgba(255,255,255,0.12);
    --chart-label:       {_with_alpha(text_color, 0.55, "#7a8fa8")};
    --chart-tooltip-bg:  rgba(12,17,35,0.95);"""
    else:
        chart_vars = """
    --chart-1: #005e9e;
    --chart-2: #d63e1a;
    --chart-3: #8a0ea8;
    --chart-4: #b51c3c;
    --chart-5: #0079b3;
    --chart-6: #b06000;
    --chart-7: #1a7a62;
    --chart-8: #5c2e9a;
    --chart-bg:          var(--bg-card, {secondary_bg});
    --chart-grid:        rgba(0,0,0,0.05);
    --chart-axis:        rgba(0,0,0,0.12);
    --chart-label:       {_with_alpha(text_color, 0.55, "#3d5370")};
    --chart-tooltip-bg:  rgba(241,244,251,0.97);"""

    return f"""
<style>
@import url('{_GOOGLE_FONTS_URL}');

/* ── Design tokens ──────────────────────────────────────────────────── */
:root {{{chart_vars}
}}

/* ── Base font assignments ──────────────────────────────────────────── */
/* Use body for inheritance — avoids breaking icon fonts on span/div    */
body {{
    font-family: {FONT_BODY} !important;
}}

/* Explicit overrides for Streamlit text components */
p, textarea,
.stMarkdown, .stMarkdown p,
.stText, .stCaption, .stAlert,
[data-testid="stSidebar"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stSelectbox"] span,
[data-testid="stMultiSelect"] span,
[data-testid="stButton"] p,
[data-testid="stCheckbox"] span[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"],
[data-testid="stCaptionContainer"] p {{
    font-family: {FONT_BODY} !important;
}}

/* Heading font — Space Grotesk */
h1, h2, h3, h4, h5, h6,
[data-testid="stHeading"] h1,
[data-testid="stHeading"] h2,
[data-testid="stHeading"] h3,
[data-testid="stHeading"] h4,
[data-testid="stHeading"] h5,
[data-testid="stHeading"] h6,
[data-testid="stMetricValue"],
[data-testid="stMetricLabel"],
.metric-value {{
    font-family: {FONT_HEADING} !important;
}}

code, pre, [data-testid="stCode"] {{
    font-family: {FONT_CODE} !important;
}}

/* Metric cards */
div[data-testid="stMetric"],
div[data-testid="metric-container"] {{
    background: linear-gradient(135deg, {bg} 0%, {secondary_bg} 100%);
    border: 1px solid {border};
    padding: 18px 22px;
    border-radius: 12px;
    box-shadow: {shadow} 0 4px 12px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    min-height: 140px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    overflow: hidden;
}}

div[data-testid="stMetric"]:hover {{
    transform: translateY(-3px);
    box-shadow: {shadow_hover} 0 8px 24px;
    border-color: {primary_border};
}}

div[data-testid="stMetric"] label {{
    font-family: {FONT_BODY} !important;
    font-weight: 500 !important;
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: {text_muted} !important;
}}

div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    font-family: {FONT_HEADING} !important;
    font-weight: 700 !important;
    font-size: 1.8rem !important;
    color: {text_color} !important;
}}

div[data-testid="stMetric"] [data-testid="stMetricDelta"] {{
    font-family: {FONT_BODY} !important;
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
    font-family: {FONT_BODY} !important;
    font-weight: 500 !important;
    font-size: 0.85rem !important;
    transition: all 0.2s ease !important;
    border: 1px solid transparent !important;
    color: {text_color} !important;
}}

div[data-testid="stRadio"] > div > label:hover {{
    background-color: {primary_light} !important;
    border-color: {primary_border} !important;
}}

div[data-testid="stRadio"] > div > label[data-checked="true"] {{
    background-color: {primary_light} !important;
    border-color: {primary} !important;
    color: {primary} !important;
}}

/* Plotly wrapper */
.main .stPlotlyChart {{
    border-radius: 8px;
}}

/* Reduce default Streamlit top whitespace so content starts near the app brand */
[data-testid="stMainBlockContainer"] {{
    padding-top: 0.75rem !important;
}}

/* Tighten the default app header/toolbar chrome by ~20px */
[data-testid="stHeader"] {{
    height: 2.5rem !important;
    min-height: 2.5rem !important;
}}

[data-testid="stToolbar"],
[data-testid="stAppToolbar"] {{
    top: 0.2rem !important;
}}

/* Reduce sidebar top space — the gap is caused by the stSidebarHeader bar (3.75rem tall
   by default) plus its marginBottom. Shrink both to push user content toward the top. */
[data-testid="stSidebarHeader"] {{
    height: 1.5rem !important;
    min-height: 1.5rem !important;
    margin-bottom: 0.25rem !important;
}}

/* Dataframe card container */
[data-testid="stDataFrame"] {{
    border: 1px solid {border} !important;
    border-radius: 10px !important;
    overflow: hidden;
    box-shadow: 0 2px 8px {shadow};
}}

/* Pagination controls sit just above the dataframe */
[data-testid="stDataFrame"] + div .stSelectbox label,
[data-testid="stDataFrame"] + div .stCaption {{
    font-family: {FONT_BODY} !important;
    color: {text_muted} !important;
    font-size: 0.78rem !important;
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
    background: {border};
    border-radius: 3px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: {primary_border};
}}
</style>
"""

def inject_theme_watcher() -> None:
    """Inject a JavaScript watcher to auto-reload on theme toggle.

    Streamlit's ``st.context.theme`` only updates on a full page reload. This
    watcher detects frontend theme changes via CSS variables and triggers a
    reload automatically. It uses an invisible iframe component and accesses
    the parent document.
    """
    import streamlit.components.v1 as components
    
    js_code = """
    <script>
    (function() {
        // Streamlit components run in an iframe, so access parent styling
        var parent = window.parent;
        var parentDoc = parent.document;
        
        // Find a reliable element (.stApp usually exists)
        function getThemeState() {
            var el = parentDoc.querySelector('[data-testid="stApp"]') 
                     || parentDoc.querySelector('.stApp') 
                     || parentDoc.body;
            var compStyle = window.parent.getComputedStyle(el);
            // Combine bg and text color for a robust check
            return compStyle.backgroundColor + ":" + compStyle.color;
        }

        function injectPlotlyCursor() {
            var iframes = parentDoc.querySelectorAll('iframe');
            iframes.forEach(function(iframe) {
                try {
                    var idoc = iframe.contentDocument || iframe.contentWindow.document;
                    // Check if it's a plotly iframe and hasn't been styled yet
                    if (idoc && idoc.querySelector('.js-plotly-plot') && !idoc.getElementById('plotly-cursor-fix')) {
                        var style = idoc.createElement('style');
                        style.id = 'plotly-cursor-fix';
                        style.innerHTML = `
                            /* Change cursor to pointer for clickable bar charts */
                            .js-plotly-plot .plotly .cursor-crosshair { cursor: pointer !important; }
                            .js-plotly-plot .plotly .nsewdrag { cursor: pointer !important; }
                            .js-plotly-plot .plotly rect { cursor: pointer !important; }
                            .js-plotly-plot .plotly path { cursor: pointer !important; }
                        `;
                        idoc.head.appendChild(style);
                    }
                } catch(e) {
                    // Ignore cross-origin errors if any
                }
            });
            // Also apply to parent doc in case Streamlit renders it natively
            if (!parentDoc.getElementById('st-plotly-cursor-fix')) {
                var style = parentDoc.createElement('style');
                style.id = 'st-plotly-cursor-fix';
                style.innerHTML = `
                    [data-testid="stPlotlyChart"] { cursor: pointer !important; }
                    .js-plotly-plot .plotly .cursor-crosshair { cursor: pointer !important; }
                    .js-plotly-plot .plotly .nsewdrag { cursor: pointer !important; }
                `;
                parentDoc.head.appendChild(style);
            }
        }

        // Wait 1.5s for Streamlit to fully render and apply CSS
        setTimeout(function() {
            var initialState = getThemeState();
            injectPlotlyCursor();
            
            setInterval(function() {
                var currentState = getThemeState();
                injectPlotlyCursor();
                
                // If the state changes and it's not a transparent glitch, user toggled theme!
                if (currentState !== initialState && currentState.indexOf("rgba(0, 0, 0, 0)") === -1 && currentState.indexOf("transparent") === -1) {
                    parent.location.reload();
                }
            }, 500);
        }, 1500);
    })();
    </script>
    """
    components.html(js_code, height=0, width=0)
