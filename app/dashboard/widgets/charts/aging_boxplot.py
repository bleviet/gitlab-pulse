"""Aging Boxplot Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


def aging_boxplot(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render boxplot of days in stage.

    Args:
        df: DataFrame of issues
        config: Optional configuration with keys:
            - group_col: column to group by (default: "stage")
            - height: chart height in pixels

    Returns:
        Selection state dictionary or None
    """
    config = config or {}
    group_col = config.get("group_col", "stage")
    height = config.get("height", 400)

    if df.empty:
        st.info("No data available for aging chart")
        return None

    days_col = "days_in_stage" if "days_in_stage" in df.columns else "age_days"
    if days_col not in df.columns:
        st.info("No age data available")
        return None

    # Only open issues for aging analysis
    open_df = df[df["state"] == "opened"].copy() if "state" in df.columns else df.copy()

    if open_df.empty:
        st.info("No open issues to analyze")
        return None

    fig = px.box(
        open_df,
        x=group_col,
        y=days_col,
        color=group_col,
        hover_data=["title", "assignee"] if "title" in open_df.columns else None,
        points="outliers",
    )

    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(gridcolor="rgba(100,116,139,0.2)", title="Days"),
    )

    selection = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        key=config.get("key", "aging_boxplot_chart"),
    )

    return selection
