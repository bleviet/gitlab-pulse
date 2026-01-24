"""Stage Distribution Chart Widget."""

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
}


def stage_distribution(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render horizontal bar chart of issues per stage (Work by Stage).

    Args:
        df: DataFrame of issues
        config: Optional configuration with keys:
            - stage_descriptions: dict mapping stage names to descriptions
            - height: chart height in pixels

    Returns:
        Selection state dictionary or None
    """
    config = config or {}
    height = config.get("height", 400)

    if df.empty or "stage" not in df.columns:
        st.info("No stage data available")
        return None

    # Count by stage
    stage_counts = df["stage"].value_counts().reset_index()
    stage_counts.columns = ["Stage", "Count"]

    # Sort by workflow order if available
    stage_order = ["Backlog", "To Do", "In Progress", "Review", "Done", "Closed"]
    stage_counts["sort_key"] = stage_counts["Stage"].apply(
        lambda x: stage_order.index(x) if x in stage_order else len(stage_order)
    )
    stage_counts = stage_counts.sort_values("sort_key").drop("sort_key", axis=1)

    # Color by stage type
    def get_stage_color(stage: str) -> str:
        stage_lower = stage.lower()
        if "done" in stage_lower or "closed" in stage_lower:
            return COLORS["completed"]
        elif "progress" in stage_lower or "review" in stage_lower:
            return COLORS["active"]
        elif "waiting" in stage_lower or "blocked" in stage_lower:
            return COLORS["waiting"]
        return COLORS["neutral"]

    stage_counts["color"] = stage_counts["Stage"].apply(get_stage_color)

    fig = px.bar(
        stage_counts,
        x="Count",
        y="Stage",
        orientation="h",
        color="Stage",
        color_discrete_map=dict(zip(stage_counts["Stage"], stage_counts["color"])),
    )

    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(gridcolor="rgba(128, 128, 128, 0.2)", title=""),
        yaxis=dict(showgrid=False, title=""),
    )

    selection = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        key=config.get("key", "stage_distribution_chart"),
    )

    return selection
