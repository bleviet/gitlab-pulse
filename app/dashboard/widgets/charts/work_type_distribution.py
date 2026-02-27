"""Work Type Distribution Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.theme import ISSUE_TYPE_COLORS, plotly_layout


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

    color_map = ISSUE_TYPE_COLORS

    fig = px.bar(
        type_counts,
        x="Count",
        y="Type",
        orientation="h",
        color="Type",
        color_discrete_map=color_map,
    )

    fig.update_traces(marker_line_width=0)

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
