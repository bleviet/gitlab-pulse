"""Error Distribution Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


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

    fig.update_layout(
        height=300,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(gridcolor="rgba(128, 128, 128, 0.2)"),
        yaxis=dict(showgrid=False),
    )

    selection = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        key=config.get("key", "error_distribution_chart") if config else "error_distribution_chart",
    )

    return selection
