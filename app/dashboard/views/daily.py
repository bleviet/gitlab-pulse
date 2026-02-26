"""Daily Report Page for Layer 3 Dashboard.

Operational snapshot of issue activity since yesterday midnight.
"""

import pandas as pd
import streamlit as st

from app.dashboard.components import style_metric_cards
from app.dashboard.widgets import charts, kpis
from app.dashboard.widgets.tables.issue_detail_grid import issue_detail_grid


# Semantic color palette
COLORS = {
    "primary": "#4F46E5",
    "active": "#3B82F6",
    "completed": "#10B981",
    "neutral": "#64748B",
}


def render_daily_report(
    df: pd.DataFrame,
    colors: dict[str, str] | None = None,
) -> None:
    """Render the Daily Report page.

    Shows issue activity since yesterday midnight (00:00 UTC):
    new issues opened, issues closed, and summary KPIs.

    Args:
        df: Filtered DataFrame with valid issues
        colors: Optional dictionary of semantic colors to override defaults
    """
    if colors:
        COLORS.update(colors)

    cutoff = pd.Timestamp.now(tz="UTC").normalize() - pd.Timedelta(days=1)
    cutoff_display = cutoff.strftime("%Y-%m-%d %H:%M UTC")

    st.header("📋 Daily Report")
    st.caption(f"Showing activity since **{cutoff_display}**")

    if df.empty:
        st.warning("No data available. Run the collector and processor first.")
        return

    # Apply Bento Grid Style
    style_metric_cards()

    # KPI Row
    kpis.daily_summary_kpi(df, {"cutoff": cutoff})

    # Activity Bar Chart
    with st.expander("📊 Activity by Type", expanded=True):
        charts.daily_activity_bar(df, {"cutoff": cutoff, "key": "daily_activity_chart"})

    # New Issues Table
    new_df = pd.DataFrame()
    if "created_at" in df.columns:
        new_df = df[df["created_at"] >= cutoff].copy()

    with st.expander(f"🆕 New Issues ({len(new_df)})", expanded=True):
        if new_df.empty:
            st.success("No new issues since yesterday midnight.")
        else:
            issue_detail_grid(
                new_df,
                config={
                    "key": "daily_new_issues_grid",
                    "columns": ["web_url", "title", "issue_type", "assignee", "severity", "milestone"],
                },
            )

    # Closed Issues Table
    closed_df = pd.DataFrame()
    if "closed_at" in df.columns:
        closed_df = df[df["closed_at"] >= cutoff].copy()

    with st.expander(f"✅ Closed Issues ({len(closed_df)})", expanded=True):
        if closed_df.empty:
            st.success("No issues closed since yesterday midnight.")
        else:
            issue_detail_grid(
                closed_df,
                config={
                    "key": "daily_closed_issues_grid",
                    "columns": ["web_url", "title", "issue_type", "assignee", "severity", "milestone"],
                },
            )
