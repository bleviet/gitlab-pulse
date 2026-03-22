"""Error Distribution Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.theme import get_palette, get_plotly_font_color, plotly_layout


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
    config = config or {}
    height = config.get("height", 150)
    widget_key = config.get("key", "error_distribution_chart")

    if quality_df.empty or "error_code" not in quality_df.columns:
        st.info("No error data available")
        return None

    error_counts = quality_df["error_code"].value_counts().reset_index()
    error_counts.columns = ["error_code", "count"]
    error_counts["label"] = (
        error_counts["error_code"]
        .astype(str)
        .str.replace("_", " ", regex=False)
        .str.title()
    )

    palette = get_palette()
    chart_colors = [
        palette["task"],
        palette["primary"],
        palette["epic"],
        palette["bug"],
        palette["high"],
        palette["feature"],
        palette["neutral"],
    ]
    color_map = {
        code: chart_colors[index % len(chart_colors)]
        for index, code in enumerate(error_counts["error_code"])
    }
    max_count = max(int(error_counts["count"].max()), 1)

    fig = px.bar(
        error_counts,
        x="count",
        y="label",
        orientation="h",
        color="error_code",
        color_discrete_map=color_map,
        text="count",
        custom_data=["error_code"],
    )

    fig.update_traces(
        marker_line_width=0,
        texttemplate="<b>%{text}</b>",
        textposition="outside",
        textfont={"color": get_plotly_font_color(), "size": 12},
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Count: %{x}<extra></extra>",
    )

    fig.update_layout(
        **plotly_layout(
            height=height,
            show_xgrid=False,
            show_ygrid=False,
            margin={"l": 0, "r": 10, "t": 20, "b": 0},
            legend_pos="none",
            bargap=0.3,
        ),
    )
    fig.update_xaxes(showgrid=False, title="", showticklabels=False, range=[0, max_count * 1.2])
    fig.update_yaxes(
        showgrid=False,
        title="",
        categoryorder="array",
        categoryarray=error_counts["label"].tolist()[::-1],
    )

    show_modebar = st.session_state.get("show_chart_controls", False)

    selection = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        selection_mode=["points"],
        key=widget_key,
        config={"displayModeBar": show_modebar},
    )

    return selection
