"""Quality Gauge Chart Widget."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# Semantic color palette
COLORS = {
    "bug": "#EF4444",
    "stale": "#F59E0B",
    "task": "#10B981",
}


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

    # Determine color based on score
    if score >= 90:
        color = COLORS["task"]
    elif score >= 70:
        color = COLORS["stale"]
    else:
        color = COLORS["bug"]

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
                {"range": [0, 70], "color": "rgba(239, 68, 68, 0.2)"},
                {"range": [70, 90], "color": "rgba(245, 158, 11, 0.2)"},
                {"range": [90, 100], "color": "rgba(16, 185, 129, 0.2)"},
            ],
            "threshold": {
                "line": {"color": COLORS["task"], "width": 2},
                "thickness": 0.75,
                "value": 90,
            },
        },
    ))

    fig.update_layout(
        height=250,
        margin=dict(l=20, r=20, t=20, b=20),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
    )

    st.plotly_chart(fig, width="stretch")
