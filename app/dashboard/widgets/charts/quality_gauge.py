"""Quality Gauge Chart Widget."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.theme import get_palette, plotly_layout, with_alpha


def quality_gauge(
    valid_df: pd.DataFrame,
    quality_df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> None:
    """Render radial gauge for quality score.

    Args:
        valid_df: DataFrame with valid issues
        quality_df: DataFrame with quality (failed) issues
        config: Optional configuration
    """
    total_valid = len(valid_df)
    total_quality = len(quality_df)
    total = total_valid + total_quality

    if total == 0:
        st.info("No data available to calculate quality score")
        return

    score = round((total_valid / total) * 100, 1)

    palette = get_palette()
    # Determine color based on score
    if score >= 90:
        color = palette["task"]
    elif score >= 70:
        color = palette["medium"]
    else:
        color = palette["bug"]

    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        number={"suffix": "%", "font": {"size": 48}},
        delta={"reference": 90, "position": "bottom"},
        gauge={
            "axis": {"range": [0, 100], "tickwidth": 1},
            "bar": {"color": color},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 70],  "color": with_alpha(palette["bug"],    0.15)},
                {"range": [70, 90], "color": with_alpha(palette["medium"], 0.15)},
                {"range": [90, 100],"color": with_alpha(palette["low"],    0.15)},
            ],
            "threshold": {
                "line": {"color": palette["task"], "width": 2},
                "thickness": 0.75,
                "value": 90,
            },
        },
    ))

    fig.update_layout(
        **plotly_layout(
            height=250,
            margin={"l": 20, "r": 20, "t": 20, "b": 20},
            legend_pos="none",
        ),
    )

    show_modebar = st.session_state.get("show_chart_controls", False)
    st.plotly_chart(fig, width="stretch", key=config.get("key", "quality_gauge_chart") if config else None, config={"displayModeBar": show_modebar})
