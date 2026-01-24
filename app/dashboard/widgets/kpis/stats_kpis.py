"""Stats KPIs Widget."""

from typing import Any

import pandas as pd
import streamlit as st

from app.dashboard.components import style_metric_cards


def stats_kpis(df: pd.DataFrame, config: dict[str, Any] | None = None) -> None:
    """Render Stats page KPI cards (Open Issues, Velocity, Bug Ratio, Stale Count).

    Args:
        df: DataFrame with valid issues
        config: Optional configuration (unused currently)
    """
    style_metric_cards()

    col1, col2, col3, col4 = st.columns(4)

    # Total Open Issues
    open_count = len(df[df["state"] == "opened"])
    with col1:
        st.metric(label="Open Issues", value=open_count)

    # Velocity (Closed per Week)
    closed_df = df[df["state"] == "closed"].copy()
    if not closed_df.empty and "closed_at" in closed_df.columns:
        closed_df["week"] = closed_df["closed_at"].dt.isocalendar().week
        weekly_closed = closed_df.groupby("week").size()
        velocity = round(weekly_closed.mean(), 1) if len(weekly_closed) > 0 else 0
    else:
        velocity = 0

    with col2:
        st.metric(label="Velocity (Closed/Week)", value=velocity)

    # Bug Ratio
    bug_count = len(df[df["issue_type"] == "Bug"])
    total_count = len(df)
    bug_ratio = round((bug_count / total_count) * 100, 1) if total_count > 0 else 0

    with col3:
        st.metric(label="Bug Ratio", value=f"{bug_ratio}%")

    # Stale Issues
    stale_count = len(df[df.get("is_stale", False) == True])
    with col4:
        st.metric(
            label="Stale Issues",
            value=stale_count,
            delta_color="inverse" if stale_count > 0 else "off",
        )
