"""Daily Activity Bar Chart Widget."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


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

    fig.add_trace(go.Bar(
        y=all_types,
        x=[int(new_counts.get(t, 0)) for t in all_types],
        name="Opened",
        orientation="h",
        marker_color="#3B82F6",
        text=[int(new_counts.get(t, 0)) for t in all_types],
        textposition="auto",
    ))

    fig.add_trace(go.Bar(
        y=all_types,
        x=[int(closed_counts.get(t, 0)) for t in all_types],
        name="Closed",
        orientation="h",
        marker_color="#10B981",
        text=[int(closed_counts.get(t, 0)) for t in all_types],
        textposition="auto",
    ))

    fig.update_layout(
        barmode="group",
        height=height,
        margin=dict(l=0, r=20, t=0, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(128, 128, 128, 0.2)",
            title="Count",
        ),
        yaxis=dict(title=""),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
    )

    st.plotly_chart(fig, width="stretch", key=widget_key)
