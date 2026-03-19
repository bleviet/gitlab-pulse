"""Overview Status Donut Chart Widget."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.theme import get_palette, get_plotly_font_color, plotly_layout


def overview_status_donut(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render status split donut chart with total count centered.

    Args:
        df: DataFrame of issues
        config: Optional configuration with keys:
            - height: chart height in pixels
            - key: unique widget key

    Returns:
        Selection state dictionary or None
    """
    config = config or {}
    height = config.get("height", 250)
    widget_key = config.get("key", "overview_status_donut")

    if df.empty or "state" not in df.columns:
        st.info("No state data available.")
        return None

    status_counts = df["state"].value_counts().reset_index()
    status_counts.columns = ["State", "Count"]

    total_issues = status_counts["Count"].sum()
    
    # Normalize state strings
    status_counts["State"] = status_counts["State"].astype(str).str.lower()
    
    open_count = status_counts[status_counts["State"] == "opened"]["Count"].sum()
    closed_count = status_counts[status_counts["State"] == "closed"]["Count"].sum()

    open_pct = round((open_count / total_issues) * 100) if total_issues > 0 else 0
    closed_pct = round((closed_count / total_issues) * 100) if total_issues > 0 else 0

    palette = get_palette()
    text_color = get_plotly_font_color()

    fig = go.Figure(data=[go.Pie(
        labels=["OPEN", "CLOSED"],
        values=[open_count, closed_count],
        hole=0.55,
        marker=dict(colors=[palette["opened"], palette["closed"]]),
        textinfo="label+percent",
        textposition="outside",
        textfont=dict(color=text_color, size=14, family="Inter, sans-serif"),
        showlegend=False,
        sort=False,
        direction="clockwise",
    )])

    # Center text annotation
    fig.add_annotation(
        text=f"<b style='font-size:32px; color:{text_color};'>{total_issues}</b><br><span style='font-size:14px; color:{text_color};'>Total</span>",
        x=0.5, y=0.5,
        font=dict(family="Inter, sans-serif"),
        showarrow=False,
        xanchor="center",
        yanchor="middle",
    )

    fig.update_layout(
        **plotly_layout(
            height=height,
            margin=dict(l=40, r=40, t=20, b=20),
            legend_pos="none",
        ),
    )

    selection = st.plotly_chart(
        fig, 
        width="stretch", 
        on_select="rerun",
        selection_mode=["points"],
        key=widget_key
    )

    return selection
