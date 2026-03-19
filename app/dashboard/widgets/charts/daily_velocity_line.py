"""Daily Velocity Line Chart Widget."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.theme import get_palette, get_plotly_font_color, plotly_layout


def daily_velocity_line(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None,
) -> dict | None:
    """Render line chart of opened vs closed issues over time.

    Args:
        df: DataFrame with valid issues
        config: Optional configuration
    """
    config = config or {}
    height = config.get("height", 300)
    widget_key = config.get("key", "daily_velocity_line")

    if df.empty:
        st.info("No data available for velocity chart.")
        return

    # Count created per day
    created_df = df[df["created_at"].notna()].copy() if "created_at" in df.columns else pd.DataFrame()
    closed_df = df[df["closed_at"].notna()].copy() if "closed_at" in df.columns else pd.DataFrame()

    if created_df.empty and closed_df.empty:
        st.info("No activity data.")
        return

    def _to_naive_date(series):
        return pd.to_datetime(series).dt.tz_localize(None).dt.floor("D")

    if not created_df.empty:
        created_df["date"] = _to_naive_date(created_df["created_at"])
        created_counts = created_df.groupby("date").size()
    else:
        created_counts = pd.Series(dtype=int)

    if not closed_df.empty:
        closed_df["date"] = _to_naive_date(closed_df["closed_at"])
        closed_counts = closed_df.groupby("date").size()
    else:
        closed_counts = pd.Series(dtype=int)

    # Combine to get full date range
    all_dates = sorted(set(created_counts.index) | set(closed_counts.index))
    if not all_dates:
        return
        
    max_date = pd.Timestamp.utcnow().tz_localize(None).floor("D")
    min_date = max_date - pd.Timedelta(days=6) # Exactly 1 week timeframe
        
    date_range = pd.date_range(start=min_date, end=max_date, freq="D")
    
    created_counts = created_counts.reindex(date_range, fill_value=0)
    closed_counts = closed_counts.reindex(date_range, fill_value=0)

    fig = go.Figure()
    palette = get_palette()
    text_color = get_plotly_font_color()

    fig.add_trace(go.Scatter(
        x=date_range,
        y=created_counts.values,
        mode="lines+markers+text",
        name="New",
        customdata=[["New"] for _ in range(len(date_range))],
        line=dict(color=palette.get("secondary", "#8e44ad"), width=2),
        marker=dict(size=8),
        text=[v if v > 0 else "" for v in created_counts.values],
        textposition="top center",
        textfont=dict(color=text_color),
    ))

    fig.add_trace(go.Scatter(
        x=date_range,
        y=closed_counts.values,
        mode="lines+markers+text",
        name="Closed",
        customdata=[["Closed"] for _ in range(len(date_range))],
        line=dict(color=palette.get("closed", "#e74c3c"), width=2),
        marker=dict(size=8),
        text=[v if v > 0 else "" for v in closed_counts.values],
        textposition="top center",
        textfont=dict(color=text_color),
    ))

    fig.update_layout(
        **plotly_layout(
            height=height,
            show_xgrid=False,
            show_ygrid=False,
            legend_pos="none",
            margin=dict(l=0, r=0, t=10, b=0),
        ),
    )
    
    # Format x-axis as MAR 01 etc
    fig.update_xaxes(
        tickformat="%b %d",
        dtick=86400000.0,
        showgrid=False
    )
    fig.update_yaxes(showgrid=False, title="ISSUE COUNT")

    show_modebar = st.session_state.get("show_chart_controls", False)

    selection = st.plotly_chart(
        fig, 
        width="stretch", 
        key=widget_key,
        on_select="rerun",
        selection_mode=["points"],
        config={"displayModeBar": show_modebar}
    )
    
    return selection
