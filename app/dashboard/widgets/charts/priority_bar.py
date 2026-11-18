"""Priority Bar Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.figure_cache import cache_figure, theme_key
from app.dashboard.theme import (
    get_palette,
    get_plotly_font_color,
    get_priority_colors,
    plotly_layout,
)


@cache_figure
def _figure(
    priority_counts: pd.DataFrame,
    colors_map: dict[str, str],
    highlight: str | None,
    dimmed: bool,
    height: int,
    theme_key: tuple[object, ...],
) -> go.Figure:
    """Build the bar figure (cached; see ``figure_cache``)."""
    fig = px.bar(
        priority_counts,
        x="Priority",
        y="Count",
        color="Priority",
        color_discrete_map=colors_map,
        orientation="v",
        text="Count",
    )
    
    fig.update_traces(
        marker_line_width=0,
        texttemplate="<b>%{text}</b>",
        textposition="outside",
        textfont=dict(color=get_plotly_font_color(), size=12) 
    )
    if highlight is not None or dimmed:
        # One trace per priority; 0.2 is the opacity Plotly gives unselected
        # points.
        for trace in fig.data:
            trace.opacity = 1.0 if trace.name == highlight else 0.2

    fig.update_layout(
        **plotly_layout(
            height=height,
            show_xgrid=False,
            show_ygrid=False,
            margin=dict(l=0, r=0, t=20, b=0),
            legend_pos="none",
        ),
    )
    
    fig.update_xaxes(showgrid=False, title="", showticklabels=True, tickfont=dict(size=10))
    fig.update_yaxes(showgrid=False, title="", showticklabels=False, range=[0, priority_counts["Count"].max() * 1.3])
    return fig


def priority_bar(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render bar chart of open issues by priority.

    Args:
        df: DataFrame of issues
        config: Optional configuration; ``highlight`` names a priority whose
            bar stays fully coloured while the others are dimmed, and
            ``dimmed`` dims every bar (for a chart beside the one whose
            selection is active). The chart draws this itself rather than
            relying on Plotly's selection, which Streamlit drops whenever the
            figure changes.
    """
    config = config or {}
    height = config.get("height", 250)
    widget_key = config.get("key", "priority_bar")

    if df.empty or "priority" not in df.columns:
        st.info("No priority data.")
        return None

    show_all = config.get("show_all", False)
    columns = [name for name in ("priority", "priority_rank") if name in df.columns]
    if not show_all and "state" in df.columns:
        work_df = df.loc[df["state"] == "opened", columns].copy()
    else:
        work_df = df[columns].copy()

    if work_df.empty:
        st.info("No issues.")
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

    if priority_counts["Count"].sum() == 0:
        return None

    palette = get_palette()
    
    colors_map = get_priority_colors()
    neutral = palette.get("neutral", "#95a5a6")
    colors_map = {
        name: colors_map.get(name, neutral) for name in priority_counts["Priority"]
    }

    if "priority_rank" in work_df.columns:
        ranks = work_df.groupby("priority")["priority_rank"].min().astype(float)
        priority_counts["Rank"] = priority_counts["Priority"].map(ranks)
    else:
        priority_counts["Rank"] = float("nan")
    priority_counts["IsUnset"] = priority_counts["Priority"] == "Unset"
    priority_counts = priority_counts.sort_values(["IsUnset", "Rank", "Priority"])

    fig = _figure(
        priority_counts,
        colors_map,
        config.get("highlight"),
        bool(config.get("dimmed")),
        height,
        theme_key(),
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
