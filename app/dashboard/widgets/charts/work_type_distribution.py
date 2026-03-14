"""Work Type Distribution Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.theme import get_palette, plotly_bar_trace_style, plotly_layout


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

    color_map = get_palette()
    issue_type_colors = {
        "Bug":     color_map["bug"],
        "Feature": color_map["feature"],
        "Task":    color_map["task"],
        "Epic":    color_map["epic"],
    }

    fig = px.bar(
        type_counts,
        x="Count",
        y="Type",
        orientation="h",
        color="Type",
        color_discrete_map=issue_type_colors,
        text="Count",
    )

    fig.update_traces(**plotly_bar_trace_style())

    fig.update_layout(
        **plotly_layout(
            height=height,
            show_xgrid=False,
            show_ygrid=False,
            legend_pos="none",
        ),
    )
    fig.update_yaxes(showgrid=False)

    st.plotly_chart(fig, width="stretch", key=config.get("key", "work_type_chart") if config else None)
