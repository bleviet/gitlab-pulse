"""Issue State Bar Chart Widget."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.theme import get_palette, get_plotly_font_color, plotly_layout


def issue_state_bar(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None,
) -> dict | None:
    """Render a horizontal bar chart of open vs closed issues."""
    config = config or {}
    height = config.get("height", 96)
    widget_key = config.get("key", "issue_state_bar")

    if df.empty or "state" not in df.columns:
        st.info("No issue state data.")
        return None

    display_df = df.drop_duplicates(subset=["id"]) if "id" in df.columns else df.copy()
    state_counts = pd.DataFrame({"state": ["opened", "closed"]})

    normalized_state_counts = (
        display_df["state"].astype(str).str.strip().str.lower().value_counts()
    )
    state_counts["count"] = (
        state_counts["state"].map(normalized_state_counts).fillna(0).astype(int)
    )
    state_counts["label"] = state_counts["state"].map(
        {
            "opened": "Open Issues",
            "closed": "Closed Issues",
        }
    )

    if state_counts["count"].sum() == 0:
        st.info("No issue state data.")
        return None

    palette = get_palette()
    color_map = {
        "opened": palette["primary"],
        "closed": palette["neutral"],
    }
    max_count = max(int(state_counts["count"].max()), 1)
    x_max = max_count * 1.2
    # Room left of zero for the row labels, so they sit inside the plot area.
    label_space = max_count * 0.6

    fig = go.Figure()
    # Transparent full-width bar per row: Plotly only reports a selection for
    # clicks on a bar, so this makes the label, count and empty space clickable.
    fig.add_bar(
        y=state_counts["label"],
        x=[x_max + label_space] * len(state_counts),
        base=-label_space,
        orientation="h",
        marker_color="rgba(0,0,0,0)",
        customdata=state_counts[["state"]],
        hovertemplate="<b>%{y}</b><extra></extra>",
    )
    fig.add_bar(
        y=state_counts["label"],
        x=state_counts["count"],
        orientation="h",
        marker_color=state_counts["state"].map(color_map),
        marker_line_width=0,
        text=state_counts["count"],
        texttemplate="<b>%{text}</b>",
        textposition="outside",
        textfont={"color": get_plotly_font_color(), "size": 12},
        cliponaxis=False,
        customdata=state_counts[["state"]],
        hovertemplate="<b>%{y}</b><br>Count: %{x}<extra></extra>",
    )
    for label in state_counts["label"]:
        fig.add_annotation(
            x=0,
            y=label,
            text=label,
            showarrow=False,
            xanchor="right",
            xshift=-8,
            font={"color": get_plotly_font_color(), "size": 13},
        )

    fig.update_layout(
        **plotly_layout(
            height=height,
            show_xgrid=False,
            show_ygrid=False,
            margin={"l": 0, "r": 10, "t": 20, "b": 0},
            legend_pos="none",
            bargap=0.3,
        ),
        barmode="overlay",
    )
    fig.update_xaxes(
        showgrid=False,
        title="",
        showticklabels=False,
        zeroline=False,
        range=[-label_space, x_max],
    )
    fig.update_yaxes(
        showgrid=False,
        title="",
        showticklabels=False,
        categoryorder="array",
        categoryarray=["Closed Issues", "Open Issues"],
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
