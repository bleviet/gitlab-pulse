"""Hygiene Page (Quality View) for Layer 3 Dashboard.

Quality scorecard and action table for data quality issues.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from app.dashboard.utils import sort_hierarchy

# Semantic color palette
COLORS = {
    "primary": "#4F46E5",
    "bug": "#EF4444",
    "feature": "#3B82F6",
    "task": "#10B981",
    "stale": "#F59E0B",
    "neutral": "#64748B",
}

# Error code severity mapping
ERROR_SEVERITY = {
    "MISSING_LABEL": "warning",
    "CONFLICTING_LABELS": "error",
    "STALE_WITHOUT_UPDATE": "warning",
    "ORPHAN_TASK": "error",
    "EXCEEDS_CYCLE_TIME": "info",
}



def render_hygiene(valid_df: pd.DataFrame, quality_df: pd.DataFrame, colors: dict[str, str] | None = None) -> None:
    """Render the Hygiene (Quality) page.

    Args:
        valid_df: DataFrame with valid issues
        quality_df: DataFrame with quality (failed) issues
        colors: Optional dictionary of semantic colors to override defaults
    """
    if colors:
        COLORS.update(colors)

    st.header("🧹 Data Hygiene")
    st.caption("Quality view for metadata cleanup and validation")

    # Quality Scorecard (Collapsible)
    with st.expander("📊 Quality Score", expanded=True):
        _render_scorecard(valid_df, quality_df)

    # Error Distribution and Action Table (Collapsible)
    if not quality_df.empty:
        with st.expander("📈 Error Distribution", expanded=True):
            _render_error_distribution(quality_df)

        with st.expander("⚡ Action Items", expanded=True):
            _render_action_table(quality_df)
    else:
        st.success("✅ Perfect data quality! All issues passed validation.")


def _render_scorecard(valid_df: pd.DataFrame, quality_df: pd.DataFrame) -> None:
    """Render radial gauge scorecard."""
    st.subheader("📊 Quality Score")

    total_valid = len(valid_df)
    total_quality = len(quality_df)
    total = total_valid + total_quality

    if total == 0:
        st.info("No data available to calculate quality score")
        return

    score = round((total_valid / total) * 100, 1)

    # Determine color based on score
    if score >= 90:
        color = COLORS["task"]
    elif score >= 70:
        color = COLORS["stale"]
    else:
        color = COLORS["bug"]

    # Create gauge chart
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        number={"suffix": "%", "font": {"size": 48}},
        delta={"reference": 90, "position": "bottom"},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": color},
            "bgcolor": "rgba(100,116,139,0.1)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 70], "color": "rgba(239,68,68,0.1)"},
                {"range": [70, 90], "color": "rgba(245,158,11,0.1)"},
                {"range": [90, 100], "color": "rgba(16,185,129,0.1)"},
            ],
            "threshold": {
                "line": {"color": COLORS["task"], "width": 4},
                "thickness": 0.75,
                "value": 90,
            },
        },
    ))

    fig.update_layout(
        margin=dict(l=20, r=20, t=40, b=20),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        height=250,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.plotly_chart(fig, width="stretch")

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Valid Issues", total_valid)
    with col2:
        st.metric("Failed Issues", total_quality)
    with col3:
        st.metric("Total Processed", total)


def _render_error_distribution(quality_df: pd.DataFrame) -> None:
    """Render error code distribution."""
    st.subheader("📋 Error Distribution")

    if "error_code" not in quality_df.columns:
        st.info("No error code data available")
        return

    error_counts = quality_df["error_code"].value_counts().reset_index()
    error_counts.columns = ["Error Code", "Count"]

    # Color mapping by severity
    def get_color(code: str) -> str:
        severity = ERROR_SEVERITY.get(code, "info")
        return {
            "error": COLORS["bug"],
            "warning": COLORS["stale"],
            "info": COLORS["neutral"],
        }.get(severity, COLORS["neutral"])

    colors = [get_color(code) for code in error_counts["Error Code"]]

    fig = go.Figure(go.Bar(
        x=error_counts["Count"],
        y=error_counts["Error Code"],
        orientation="h",
        marker_color=colors,
    ))

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(100,116,139,0.2)", title="Count"),
        yaxis=dict(showgrid=False, title=""),
        height=200,
    )

    st.plotly_chart(fig, width="stretch")


def _render_action_table(quality_df: pd.DataFrame) -> None:
    """Render action table with failed issues."""
    st.subheader("🔧 Action Required")

    # Select display columns
    display_cols = ["web_url", "title", "error_code", "error_message", "assignee"]
    available_cols = [c for c in display_cols if c in quality_df.columns]

    display_df = quality_df[available_cols].copy()
    
    if "parent_id" in display_df.columns:
         display_df = sort_hierarchy(display_df, parent_col="parent_id", id_col="iid", title_col="title")

    # Rename for display
    display_df = display_df.rename(columns={"web_url": "IID", "title": "Title", "error_code": "Error", "error_message": "Details", "assignee": "Assignee"})

    # Style the error_code (now 'Error') column
    def style_error_code(row: pd.Series) -> list[str]:
        code = row.get("Error", "")
        severity = ERROR_SEVERITY.get(code, "info")
        bg_colors = {
            "error": "background-color: rgba(239,68,68,0.2)",
            "warning": "background-color: rgba(245,158,11,0.2)",
            "info": "background-color: rgba(100,116,139,0.1)",
        }
        style = bg_colors.get(severity, "")
        return [style if c == "Error" else "" for c in row.index]

    st.dataframe(
        display_df.style.apply(style_error_code, axis=1),
        width="stretch",
        hide_index=True,
        column_order=["IID", "Title", "Error", "Details", "Assignee"],
        column_config={
            "IID": st.column_config.LinkColumn(
                "IID", 
                display_text=r"/(?:issues|work_items)/(\d+)$", 
                width="small"
            ),
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Error": st.column_config.TextColumn("Error", width="medium"),
            "Details": st.column_config.TextColumn("Details", width="large"),
            "Assignee": st.column_config.TextColumn("Assignee", width="medium"),
        },
    )
