"""Work Type Distribution Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

# Semantic color palette
COLORS = {
    "bug": "#EF4444",
    "feature": "#3B82F6",
    "task": "#10B981",
    "epic": "#8B5CF6",
}


def work_type_distribution(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> None:
    """Render horizontal bar chart of issue type distribution.

    Args:
        df: DataFrame of issues
        config: Optional configuration with keys:
            - height: chart height in pixels
    """
    config = config or {}
    height = config.get("height", 300)

    if "issue_type" not in df.columns or df["issue_type"].isna().all():
        st.info("No issue type data available")
        return

    type_counts = df["issue_type"].value_counts().reset_index()
    type_counts.columns = ["Type", "Count"]

    color_map = {
        "Bug": COLORS["bug"],
        "Feature": COLORS["feature"],
        "Task": COLORS["task"],
        "Epic": COLORS["epic"],
    }

    fig = px.bar(
        type_counts,
        x="Count",
        y="Type",
        orientation="h",
        color="Type",
        color_discrete_map=color_map,
    )

    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(gridcolor="rgba(128, 128, 128, 0.2)"),
        yaxis=dict(showgrid=False),
    )

    st.plotly_chart(fig, width="stretch")
