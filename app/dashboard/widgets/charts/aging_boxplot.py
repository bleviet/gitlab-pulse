"""Aging Boxplot Chart Widget.

Refactored to support advanced features from overview.py:
- Coloring by stage type (active/waiting)
- Sorting by stage workflow order
- Enhanced hover data
"""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.theme import get_palette, get_stage_colors, plotly_layout


def aging_boxplot(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render boxplot of days in stage.
    
    Features:
    - Colors boxes by stage type (active/waiting) if available, otherwise by stage
    - Sorts x-axis by stage workflow order
    - Shows outliers
    - Tooltips with issue details

    Args:
        df: DataFrame of issues
        config: Optional configuration with keys:
            - group_col: column to group by (default: "stage")
            - height: chart height in pixels
            - filter_closed: bool, whether to filter out closed/completed items (default: True)

    Returns:
        Selection state dictionary or None
    """
    config = config or {}
    group_col = config.get("group_col", "stage")
    height = config.get("height", 400)
    filter_closed = config.get("filter_closed", True)
    widget_key = config.get("key", "aging_boxplot")

    if df.empty:
        st.info("No data available for aging chart")
        return None

    days_col = "days_in_stage" if "days_in_stage" in df.columns else "age_days"
    if days_col not in df.columns:
        st.info("No age data available")
        return None

    # Filter logic similar to overview.py: focus on active work
    df_plot = df.copy()
    if filter_closed:
        # Filter out completed stage items if stage_type exists
        if "stage_type" in df_plot.columns:
            df_plot = df_plot[df_plot["stage_type"] != "completed"]
        
        # Filter out closed issues
        if "state" in df_plot.columns:
            df_plot = df_plot[df_plot["state"] != "closed"]

    if df_plot.empty:
        st.info("No active issues to analyze")
        return None

    # Sorting logic
    category_orders = {}
    if group_col == "stage":
        if "stage_order" in df_plot.columns:
            # Sort by stage_order
            stage_orders = df_plot.groupby("stage")["stage_order"].min().sort_values()
            sorted_stages = stage_orders.index.tolist()
            category_orders["stage"] = sorted_stages
            # Ensure df is sorted for Plotly
            df_plot["stage"] = pd.Categorical(df_plot["stage"], categories=sorted_stages, ordered=True)
            df_plot = df_plot.sort_values("stage")

    # Coloring logic
    color_col = group_col
    color_map = None
    palette = get_palette()
    stage_colors = get_stage_colors()
    
    if "stage_type" in df_plot.columns and group_col == "stage":
        color_col = "stage_type"
        color_map = stage_colors.copy()
        # Ensure we don't have missing keys that cause errors
        unique_types = df_plot["stage_type"].astype(str).unique()
        for t in unique_types:
            if t not in color_map:
                color_map[t] = palette["neutral"]

    fig = px.box(
        df_plot,
        x=group_col,
        y=days_col,
        color=color_col,
        color_discrete_map=color_map,
        hover_data=["title", "assignee"] if "title" in df_plot.columns else None,
        points="outliers",
        category_orders=category_orders
    )

    show_legend = color_col != group_col

    fig.update_layout(
        **plotly_layout(
            height=height,
            show_xgrid=False,
            show_ygrid=True,
        ),
    )
    fig.update_layout(showlegend=show_legend)
    fig.update_xaxes(showgrid=False, title="")
    fig.update_yaxes(gridcolor="rgba(148, 163, 184, 0.18)", title="Days in Stage")

    selection = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        key=widget_key,
    )

    return selection
