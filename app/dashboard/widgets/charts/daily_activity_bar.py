"""Daily Activity Bar Chart Widget."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.theme import get_palette, plotly_layout


def daily_activity_bar(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None,
) -> None:
    """Render grouped bar chart of opened vs closed issues by type.

    Shows issue activity since yesterday midnight, grouped by issue_type.

    Args:
        df: DataFrame with valid issues
        config: Optional configuration with keys:
            - cutoff: pd.Timestamp for the cutoff (default: yesterday 00:00 UTC)
            - height: chart height in pixels
            - key: unique Streamlit widget key
    """
    config = config or {}
    cutoff = config.get(
        "cutoff",
        pd.Timestamp.now(tz="UTC").normalize() - pd.Timedelta(days=1),
    )
    height = config.get("height", 350)
    widget_key = config.get("key", "daily_activity_bar")

    if df.empty:
        st.info("No data available for daily activity chart.")
        return

    type_col = "issue_type" if "issue_type" in df.columns else None

    new_df = df[df["created_at"] >= cutoff] if "created_at" in df.columns else pd.DataFrame()
    closed_df = df[df["closed_at"] >= cutoff] if "closed_at" in df.columns else pd.DataFrame()

    if new_df.empty and closed_df.empty:
        st.info("No issue activity since yesterday midnight.")
        return

    if type_col:
        new_counts = new_df[type_col].value_counts()
        closed_counts = closed_df[type_col].value_counts()
        all_types = sorted(set(new_counts.index) | set(closed_counts.index))
    else:
        new_counts = pd.Series({"All": len(new_df)})
        closed_counts = pd.Series({"All": len(closed_df)})
        all_types = ["All"]

    fig = go.Figure()

    palette = get_palette()
    fig.add_trace(go.Bar(
        y=all_types,
        x=[int(new_counts.get(t, 0)) for t in all_types],
        name="Opened",
        orientation="h",
        marker_color=palette["opened"],
        marker_line_width=0,
        text=[int(new_counts.get(t, 0)) for t in all_types],
        textposition="auto",
    ))

    fig.add_trace(go.Bar(
        y=all_types,
        x=[int(closed_counts.get(t, 0)) for t in all_types],
        name="Closed",
        orientation="h",
        marker_color=palette["closed"],
        marker_line_width=0,
        text=[int(closed_counts.get(t, 0)) for t in all_types],
        textposition="auto",
    ))

    fig.update_layout(
        **plotly_layout(
            height=height,
            show_xgrid=False,
            show_ygrid=False,
        ),
        barmode="group",
    )
    fig.update_xaxes(showgrid=False, title="Count")
    fig.update_yaxes(title="")

    st.plotly_chart(fig, width="stretch", key=widget_key)
