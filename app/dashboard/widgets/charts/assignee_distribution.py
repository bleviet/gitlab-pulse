"""Assignee Distribution Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.theme import get_palette, get_plotly_font_color, plotly_layout


def assignee_distribution(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render vertical bar chart of open issues by assignee.

    Args:
        df: DataFrame of issues
        config: Optional config

    Returns:
        Selection state dictionary or None
    """
    config = config or {}
    height = config.get("height", 250)
    widget_key = config.get("key", "assignee_distribution")

    if df.empty or "assignee" not in df.columns:
        st.info("No assignee data.")
        return None

    work_df = df[df["state"] == "opened"].copy() if "state" in df.columns else df.copy()

    if work_df.empty:
        st.info("No open issues.")
        return None

    # Group by Assignee
    agg_df = work_df.groupby("assignee").size().reset_index(name="count")
    agg_df = agg_df.sort_values(by="count", ascending=False)
    
    # Take top 6
    agg_df = agg_df.head(6)

    palette = get_palette()
    bar_color = palette.get("primary", "#1abc9c")

    fig = px.bar(
        agg_df,
        x="assignee",
        y="count",
        orientation="v",
    )
    
    fig.update_traces(
        marker_color=bar_color,
        marker_line_width=0,
        text=[f"<b>{c}</b><br>Open" for c in agg_df["count"]],
        textposition="inside",
        insidetextanchor="middle",
        textfont=dict(color="#ffffff") 
    )

    fig.update_layout(
        **plotly_layout(
            height=height,
            show_xgrid=False,
            show_ygrid=False,
            margin=dict(l=0, r=0, t=10, b=0),
        ),
    )
    
    fig.update_xaxes(showgrid=False, title="")
    fig.update_yaxes(showgrid=False, title="", showticklabels=False)

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
