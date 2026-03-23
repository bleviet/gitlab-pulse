"""Status Donut Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.theme import get_palette, plotly_layout


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

    palette = get_palette()
    color_map = {
        "opened": palette["opened"],
        "closed": palette["closed"],
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
        **plotly_layout(
            height=300,
            margin={"l": 0, "r": 0, "t": 10, "b": 0},
            legend_pos="none",
        ),
    )
    fig.update_layout(
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.1),
    )

    show_modebar = st.session_state.get("show_chart_controls", False)
    st.plotly_chart(fig, width="stretch", key=config.get("key", "status_donut_chart") if config else None, config={"displayModeBar": show_modebar})
