"""Workload Distribution Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.theme import get_palette, get_stage_colors, plotly_layout


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

    palette = get_palette()
    stage_colors = get_stage_colors()

    fig = px.bar(
        agg_df,
        x="count",
        y="assignee",
        color="stage",
        orientation="h",
        color_discrete_map={
            "Backlog": stage_colors.get("backlog", palette["neutral"]),
            "To Do": stage_colors.get("waiting", palette["waiting"]),
            "In Progress": stage_colors.get("active", palette["active"]),
            "Review": stage_colors.get("review", palette["primary"]),
            "Done": stage_colors.get("completed", palette["completed"]),
        },
    )

    fig.update_traces(marker_line_width=0)

    fig.update_layout(
        **plotly_layout(
            height=height,
            show_xgrid=False,
            show_ygrid=False,
        ),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(148, 163, 184, 0.18)", title="Issue Count")
    fig.update_yaxes(showgrid=False, title="")

    # Add threshold line
    fig.add_vline(x=threshold, line_dash="dash", line_color=palette["stale"])

    selection = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        key=config.get("key", "workload_distribution_chart"),
    )

    return selection
