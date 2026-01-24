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

# Semantic color palette
COLORS = {
    "primary": "#4F46E5",
    "active": "#3B82F6",
    "waiting": "#F59E0B",
    "completed": "#10B981",
    "neutral": "#64748B",
}


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
    
    if "stage_type" in df_plot.columns and group_col == "stage":
        color_col = "stage_type"
        color_map = {
            "active": COLORS["active"],
            "waiting": COLORS["waiting"],
            "completed": COLORS["completed"],
            # Fallback for others
            "backlog": COLORS["neutral"],
            "triage": COLORS["neutral"],
        }
        # Ensure we don't have missing keys that cause errors
        unique_types = df_plot["stage_type"].astype(str).unique()
        for t in unique_types:
            if t not in color_map:
                color_map[t] = COLORS["neutral"]

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

    fig.update_layout(
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True if color_col != group_col else False,
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(gridcolor="rgba(100,116,139,0.2)", title="Days in Stage"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None)
    )

    selection = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        key=widget_key,
    )

    return selection
