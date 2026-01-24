"""Hygiene Page (Quality View) for Layer 3 Dashboard.

Quality scorecard and action table for data quality issues.
Refactored to use Widget Registry.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.utils import sort_hierarchy
from app.dashboard.widgets import charts
from app.dashboard.components import style_metric_cards

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

    # Apply Bento Grid Style
    style_metric_cards()

    # Quality Scorecard (Collapsible) - using widget
    with st.expander("📊 Quality Score", expanded=True):
        charts.quality_gauge(valid_df, quality_df)
        # Summary metrics
        total_valid = len(valid_df)
        total_quality = len(quality_df)
        total = total_valid + total_quality
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Valid Issues", total_valid)
        with col2:
            st.metric("Failed Issues", total_quality)
        with col3:
            st.metric("Total Processed", total)

    # Error Distribution and Action Table (Collapsible)
    if not quality_df.empty:
        selection = None
        with st.expander("📈 Error Distribution", expanded=True):
            selection = charts.error_distribution(quality_df)

        # Filter Action Table based on selection
        filtered_df = quality_df.copy()
        if selection and selection.get("selection", {}).get("points"):
            selected_points = selection["selection"]["points"]
            # Error code is on the Y axis
            selected_errors = [p["y"] for p in selected_points]
            if selected_errors:
                filtered_df = filtered_df[filtered_df["error_code"].isin(selected_errors)]

        with st.expander("⚡ Action Items", expanded=True):
            _render_action_table(filtered_df)
    else:
        st.success("✅ Perfect data quality! All issues passed validation.")


def _render_action_table(quality_df: pd.DataFrame) -> None:
    """Render action table with failed issues (custom styling preserved)."""
    # Select display columns
    display_cols = ["web_url", "title", "error_code", "error_message", "assignee"]
    available_cols = [c for c in display_cols if c in quality_df.columns]

    display_df = quality_df[available_cols].copy()

    if "parent_id" in display_df.columns:
        display_df = sort_hierarchy(display_df, parent_col="parent_id", id_col="iid", title_col="title")

    # Rename for display
    display_df = display_df.rename(columns={
        "web_url": "IID",
        "title": "Title",
        "error_code": "Error",
        "error_message": "Details",
        "assignee": "Assignee"
    })

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
        height=800,
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
