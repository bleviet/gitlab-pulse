"""Priority Donut Chart Widget."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.theme import (
    get_active_theme_mode,
    get_palette,
    get_plotly_font_color,
    get_priority_colors,
    get_streamlit_theme_color,
    plotly_layout,
)


def priority_donut(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render donut chart of open issues by priority.

    Args:
        df: DataFrame of issues
        config: Optional configuration
    """
    config = config or {}
    height = config.get("height", 250)
    widget_key = config.get("key", "priority_donut")
    center_text = config.get("center_text", "OPEN<br>ISSUES")
    show_legend = config.get("show_legend", True)

    if df.empty or "priority" not in df.columns:
        st.info("No priority data available.")
        return None

    state_filter = config.get("state_filter", "opened")
    if "state" in df.columns:
        if state_filter == "all":
            work_df = df.copy()
        else:
            work_df = df[df["state"] == state_filter].copy()
    else:
        work_df = df.copy()

    if work_df.empty:
        st.info(f"No {state_filter if state_filter != 'all' else ''} issues.")
        return None

    # Normalize priority: missing values become "Unset"
    priority = work_df["priority"].astype(object)
    priority_text = priority.astype(str).str.strip()
    is_unset = priority.isna() | priority_text.str.lower().isin(
        ["", "none", "nan", "<na>"]
    )
    work_df["priority"] = priority_text.where(~is_unset, "Unset")

    priority_counts = work_df["priority"].value_counts().reset_index()
    priority_counts.columns = ["Priority", "Count"]

    total_issues = priority_counts["Count"].sum()
    if total_issues == 0:
        return None

    palette = get_palette()
    
    colors_map = get_priority_colors()
    neutral = palette.get("neutral", "#95a5a6")

    if "priority_rank" in work_df.columns:
        ranks = work_df.groupby("priority")["priority_rank"].min().astype(float)
        priority_counts["Rank"] = priority_counts["Priority"].map(ranks)
    else:
        priority_counts["Rank"] = float("nan")
    priority_counts["IsUnset"] = priority_counts["Priority"] == "Unset"
    priority_counts = priority_counts.sort_values(["IsUnset", "Rank", "Priority"])
    
    labels = priority_counts["Priority"].tolist()
    values = priority_counts["Count"].tolist()
    colors = [colors_map.get(lbl, neutral) for lbl in labels]

    text_color = get_plotly_font_color()
    mode = get_active_theme_mode()
    bg_color = get_streamlit_theme_color("backgroundColor", "#050811" if mode == "dark" else "#f8f9fc")

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(
            colors=colors,
            line=dict(color=bg_color, width=2)
        ),
        textinfo="value",
        textposition="inside",
        textfont=dict(color="#ffffff", size=12),
        showlegend=show_legend,
        sort=False,
    )])

    fig.add_annotation(
        text=f"<b style='font-size:28px; color:{text_color};'>{total_issues}</b><br><span style='font-size:12px; color:{text_color};'>{center_text}</span>",
        x=0.5, y=0.5,
        font=dict(family="Inter, sans-serif"),
        showarrow=False,
        xanchor="center",
        yanchor="middle",
    )

    fig.update_layout(
        **plotly_layout(
            height=height,
            margin=dict(l=0, r=0 if not show_legend else 20, t=10, b=10),
            legend_pos="right" if show_legend else "none",
        ),
    )
    
    fig.update_layout(
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.0
        )
    )

    show_modebar = st.session_state.get("show_chart_controls", False)

    selection = st.plotly_chart(
        fig, 
        width="stretch", 
        on_select="rerun",
        selection_mode=["points"],
        key=widget_key,
        config={"displayModeBar": show_modebar}
    )

    return selection
