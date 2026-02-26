"""Aging Page (Operational View) for Layer 3 Dashboard.

Boxplots for age distribution and stale issue alerts.
Refactored to use Widget Registry.
"""

import pandas as pd
import streamlit as st

from app.dashboard.widgets import tables, charts
from app.dashboard.widgets.tables.issue_detail_grid import issue_detail_grid
from app.dashboard.components import style_metric_cards


# Semantic color palette
COLORS = {
    "primary": "#4F46E5",
    "bug": "#EF4444",
    "feature": "#3B82F6",
    "task": "#10B981",
    "stale": "#F59E0B",
    "neutral": "#64748B",
    "epic": "#8B5CF6",
}


def render_aging(df: pd.DataFrame, colors: dict[str, str] | None = None) -> None:
    """Render the Aging (Operational) page.

    Args:
        df: Filtered DataFrame with valid issues
        colors: Optional dictionary of semantic colors to override defaults
    """
    if colors:
        COLORS.update(colors)

    st.header("⏱️ Aging Analysis")
    st.caption("Operational view for identifying bottlenecks")

    if df.empty:
        st.warning("No data available. Run the collector and processor first.")
        return

    # Alert Banner for stale issues
    _render_stale_alert(df)

    # Apply Bento Grid Style
    style_metric_cards()

    # Boxplot by Issue Type (Collapsible) - using widget
    with st.expander("📊 Age Distribution by Type", expanded=True):
        charts.aging_boxplot(df, {"group_col": "issue_type", "key": "aging_by_type"})

    # Boxplot by Severity (Collapsible)
    if "severity" in df.columns and not df["severity"].isna().all():
        with st.expander("📊 Age Distribution by Severity", expanded=True):
            charts.aging_boxplot(df, {"group_col": "severity", "key": "aging_by_severity"})

    # Stale Issues Table (Collapsible) - using widget
    with st.expander("⚠️ Stale Issues", expanded=True):
        st.subheader("📋 Stale Issues List")
        stale_df = df[df["is_stale"] == True] if "is_stale" in df.columns else pd.DataFrame()
        if stale_df.empty:
            st.success("✅ No stale issues! All issues are actively maintained.")
        else:
            tables.issue_detail_grid(
                stale_df,
                config={
                    "columns": ["web_url", "title", "issue_type", "assignee", "age_days", "updated_at"],
                    "column_config": {
                        "Age (Days)": st.column_config.NumberColumn("Age (Days)", width="small"),
                        "Last Update": st.column_config.TextColumn("Last Update", width="medium"),
                    },
                    "title": "📋 Stale Issues List",
                    "key": "stale_issues_grid"
                }
            )


def _render_stale_alert(df: pd.DataFrame) -> None:
    """Render alert banner if too many stale issues."""
    if "is_stale" not in df.columns:
        return

    stale_count = len(df[df["is_stale"] == True])
    open_count = len(df[df["state"] == "opened"])

    if open_count == 0:
        return

    stale_ratio = stale_count / open_count

    if stale_ratio > 0.2:  # More than 20% stale
        st.warning(
            f"**High volume of stale issues detected!** "
            f"{stale_count} issues ({stale_ratio:.0%} of open) have not been updated recently.",
            icon="⚠️",
        )
    elif stale_count > 0:
        st.info(
            f"{stale_count} stale issue(s) need attention.",
            icon="ℹ️",
        )
