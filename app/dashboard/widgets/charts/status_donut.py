"""Status Donut Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

# Semantic color palette
COLORS = {
    "stale": "#F59E0B",
    "task": "#10B981",
}


def status_donut(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> None:
    """Render status split donut chart.

    Args:
        df: DataFrame of issues
        config: Optional configuration with keys:
            - height: chart height in pixels
    """
    config = config or {}

    status_counts = df["state"].value_counts().reset_index()
    status_counts.columns = ["State", "Count"]

    color_map = {
        "opened": COLORS["stale"],
        "closed": COLORS["task"],
    }

    fig = px.pie(
        status_counts,
        values="Count",
        names="State",
        hole=0.6,
        color="State",
        color_discrete_map=color_map,
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.1),
    )

    st.plotly_chart(fig, width="stretch")
