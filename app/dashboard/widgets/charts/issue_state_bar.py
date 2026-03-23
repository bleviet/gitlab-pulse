"""Issue State Bar Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
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

    fig = px.bar(
        state_counts,
        x="count",
        y="label",
        orientation="h",
        color="state",
        color_discrete_map=color_map,
        text="count",
        custom_data=["state"],
    )

    fig.update_traces(
        marker_line_width=0,
        texttemplate="<b>%{text}</b>",
        textposition="outside",
        textfont={"color": get_plotly_font_color(), "size": 12},
        cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Count: %{x}<extra></extra>",
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
    )
    fig.update_xaxes(showgrid=False, title="", showticklabels=False, range=[0, max_count * 1.2])
    fig.update_yaxes(
        showgrid=False,
        title="",
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
