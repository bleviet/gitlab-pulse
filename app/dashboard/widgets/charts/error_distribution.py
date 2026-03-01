"""Error Distribution Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.theme import plotly_layout


def error_distribution(
    quality_df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render horizontal bar chart of error code distribution.

    Args:
        quality_df: DataFrame with quality issues
        config: Optional configuration

    Returns:
        Selection state dictionary or None
    """
    if quality_df.empty or "error_code" not in quality_df.columns:
        st.info("No error data available")
        return None

    error_counts = quality_df["error_code"].value_counts().reset_index()
    error_counts.columns = ["Error Code", "Count"]

    fig = px.bar(
        error_counts,
        x="Count",
        y="Error Code",
        orientation="h",
        color="Error Code",
    )

    fig.update_traces(marker_line_width=0)

    fig.update_layout(
        **plotly_layout(
            height=300,
            show_xgrid=False,
            show_ygrid=False,
            legend_pos="none",
        ),
    )
    fig.update_yaxes(showgrid=False)

    selection = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        key=config.get("key", "error_distribution_chart") if config else "error_distribution_chart",
    )

    return selection
