"""Error Distribution Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.theme import get_palette, plotly_bar_trace_style, plotly_layout


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

    palette = get_palette()
    # Map error codes to semantic severity colors
    _SEVERITY_COLORS: dict[str, str] = {
        "CONFLICTING_LABELS":    palette["bug"],
        "ORPHAN_TASK":           palette["bug"],
        "MISSING_LABEL":         palette["high"],
        "STALE_WITHOUT_UPDATE":  palette["high"],
        "EXCEEDS_CYCLE_TIME":    palette["neutral"],
    }
    color_map = {
        code: _SEVERITY_COLORS.get(code, palette["neutral"])
        for code in error_counts["Error Code"]
    }

    fig = px.bar(
        error_counts,
        x="Count",
        y="Error Code",
        orientation="h",
        color="Error Code",
        color_discrete_map=color_map,
        text="Count",
    )

    fig.update_traces(**plotly_bar_trace_style())

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
