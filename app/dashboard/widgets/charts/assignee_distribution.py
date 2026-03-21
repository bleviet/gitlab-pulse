"""Assignee Distribution Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.theme import get_palette, get_plotly_font_color, plotly_layout
from app.dashboard.utils import normalize_assignee_labels


def assignee_distribution(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render a top-N vertical bar chart of issue counts by assignee.

    Args:
        df: DataFrame of issues
        config: Optional config

    Returns:
        Selection state dictionary or None
    """
    config = config or {}
    height = config.get("height", 250)
    limit = int(config.get("limit", 5))
    widget_key = config.get("key", "assignee_distribution")

    if df.empty or "assignee" not in df.columns:
        st.info("No assignee data.")
        return None

    display_df = df.drop_duplicates(subset=["id"]).copy() if "id" in df.columns else df.copy()

    if display_df.empty:
        st.info("No issue data.")
        return None

    assignee_labels = normalize_assignee_labels(display_df["assignee"])
    agg_df = (
        assignee_labels.value_counts()
        .head(limit)
        .rename_axis("assignee")
        .reset_index(name="count")
    )

    if agg_df.empty:
        st.info("No assignee data.")
        return None

    palette = get_palette()
    bar_colors = [palette["primary"]] + [palette["opened"]] * max(len(agg_df) - 1, 0)
    max_count = max(int(agg_df["count"].max()), 1)

    fig = px.bar(
        agg_df,
        x="assignee",
        y="count",
        orientation="v",
        text="count",
        category_orders={"assignee": agg_df["assignee"].tolist()},
    )

    fig.update_traces(
        marker_color=bar_colors,
        marker_line_width=0,
        texttemplate="<b>%{text}</b>",
        textposition="outside",
        textfont={"color": get_plotly_font_color(), "size": 12},
        cliponaxis=False,
        hovertemplate="<b>%{x}</b><br>Issues: %{y}<extra></extra>",
    )

    fig.update_layout(
        **plotly_layout(
            height=height,
            show_xgrid=False,
            show_ygrid=False,
            margin=dict(l=0, r=0, t=12, b=16),
            bargap=0.34,
            legend_pos="none",
        ),
    )

    fig.update_xaxes(showgrid=False, title="", tickangle=0, automargin=True)
    fig.update_yaxes(
        showgrid=False,
        title="",
        showticklabels=False,
        range=[0, max_count * 1.22],
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
