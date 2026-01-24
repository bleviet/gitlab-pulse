"""Workload Distribution Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

# Semantic color palette
COLORS = {
    "primary": "#4F46E5",
    "active": "#3B82F6",
    "waiting": "#F59E0B",
    "completed": "#10B981",
    "neutral": "#64748B",
    "stale": "#F59E0B",
}


def workload_distribution(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render stacked bar chart of assignee vs issue count by stage.

    Args:
        df: DataFrame of issues
        config: Optional configuration with keys:
            - threshold: WIP limit threshold for coloring
            - height: chart height in pixels

    Returns:
        Selection state dictionary or None
    """
    config = config or {}
    threshold = config.get("threshold", 5)
    height = config.get("height", 400)

    if df.empty or "assignee" not in df.columns:
        st.info("No assignee data available")
        return None

    # Aggregate by assignee and stage
    work_df = df[df["state"] == "opened"].copy() if "state" in df.columns else df.copy()

    if work_df.empty:
        st.info("No open issues to analyze")
        return None

    agg_df = work_df.groupby(["assignee", "stage"]).size().reset_index(name="count")

    fig = px.bar(
        agg_df,
        x="count",
        y="assignee",
        color="stage",
        orientation="h",
        color_discrete_map={
            "Backlog": COLORS["neutral"],
            "To Do": COLORS["waiting"],
            "In Progress": COLORS["active"],
            "Review": COLORS["primary"],
            "Done": COLORS["completed"],
        },
    )

    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(gridcolor="rgba(128, 128, 128, 0.2)", title="Issue Count"),
        yaxis=dict(showgrid=False, title=""),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )

    # Add threshold line
    fig.add_vline(x=threshold, line_dash="dash", line_color=COLORS["stale"])

    selection = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        key=config.get("key", "workload_distribution_chart"),
    )

    return selection
