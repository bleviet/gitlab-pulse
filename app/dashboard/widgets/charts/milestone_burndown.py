"""Milestone Burndown Chart Widget."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.theme import get_palette, get_plotly_font_color, plotly_layout, with_alpha


def milestone_burndown(
    df: pd.DataFrame,
    milestone_meta: pd.Series | dict,
    config: dict[str, Any] | None = None
) -> None:
    """Render burndown chart (Remaining vs Ideal) for a milestone.
    
    Args:
        df: DataFrame of issues in the milestone
        milestone_meta: Dictionary/Series with milestone_start_date, milestone_due_date
        config: Optional configuration
    """
    config = config or {}
    height = config.get("height", 350)
    widget_key = config.get("key", "milestone_burndown")

    if getattr(milestone_meta, "empty", False):
        milestone_meta = {}

    def to_naive_utc(ts):
        if pd.isna(ts): return pd.NaT
        ts = pd.to_datetime(ts)
        if ts.tz is not None:
            ts = ts.tz_convert(None)
        return ts

    start_date = to_naive_utc(milestone_meta.get("milestone_start_date") if isinstance(milestone_meta, dict) or "milestone_start_date" in milestone_meta else pd.NaT)
    
    if pd.isna(start_date):
        if not df.empty and "created_at" in df.columns:
            start_date = to_naive_utc(df["created_at"].min())
        else:
            start_date = pd.Timestamp.utcnow().replace(tzinfo=None)

    end_date = to_naive_utc(milestone_meta.get("milestone_due_date") if isinstance(milestone_meta, dict) or "milestone_due_date" in milestone_meta else pd.NaT)
    now = pd.Timestamp.utcnow().replace(tzinfo=None).normalize()

    if pd.isna(end_date):
        end_date = now + pd.Timedelta(days=14)

    if pd.isna(start_date):
        start_date = now

    start_date = start_date.floor("D")
    end_date = end_date.floor("D")

    if end_date < start_date:
        end_date = start_date + pd.Timedelta(days=14)

    timeline = pd.date_range(start=start_date, end=max(end_date, now), freq="D")

    total_issues = len(df)
    
    if not df.empty and "closed_at" in df.columns:
        completed_df = df[df["state"] == "closed"].copy()
        if not completed_df.empty:
            completed_df["closed_date"] = pd.to_datetime(completed_df["closed_at"]).apply(to_naive_utc).dt.floor("D")
            completed_counts = completed_df.groupby("closed_date").size().sort_index().cumsum()
        else:
            completed_counts = pd.Series(dtype=int, index=pd.to_datetime([]))
    else:
        completed_counts = pd.Series(dtype=int, index=pd.to_datetime([]))

    completed_series = completed_counts.reindex(timeline, method='ffill').fillna(0)
    
    # Actual remaining
    remaining_series = total_issues - completed_series
    
    # Cap to now, don't show remaining in the future
    future_mask = timeline > now
    remaining_series.loc[future_mask] = None

    # Ideal burndown
    total_days = (end_date - start_date).days
    if total_days <= 0:
        total_days = 1
        
    ideal_slope = total_issues / total_days
    ideal_series = [max(0, total_issues - (ideal_slope * (d - start_date).days)) for d in timeline]

    fig = go.Figure()
    palette = get_palette()

    fig.add_trace(go.Scatter(
        x=timeline,
        y=ideal_series,
        mode='lines',
        name='Ideal Burndown',
        line=dict(shape='linear', color=palette["neutral"], dash='dash'),
    ))

    # To handle None values safely without breaking filled areas
    valid_remaining = remaining_series.dropna()
    valid_timeline = timeline[~future_mask]

    fig.add_trace(go.Scatter(
        x=valid_timeline,
        y=valid_remaining,
        mode='lines+text',
        name='Actual Remaining',
        fill='tozeroy',
        line=dict(color=palette.get("secondary", "#9b59b6")),
        fillcolor=with_alpha(palette.get("secondary", "#9b59b6"), 0.25),
        text=[int(v) if pd.notna(v) else "" for v in valid_remaining],
        textposition='top center',
        textfont=dict(color=get_plotly_font_color(), size=10)
    ))

    fig.update_layout(
        **plotly_layout(
            height=height,
            show_xgrid=False,
            show_ygrid=False,
            legend_pos="top",
            margin=dict(l=0, r=0, t=30, b=0),
        )
    )
    
    fig.update_xaxes(
        tickformat="%b %d",
        dtick=86400000.0,
        showgrid=False
    )
    fig.update_yaxes(showgrid=False)

    show_modebar = st.session_state.get("show_chart_controls", False)
    st.plotly_chart(fig, width="stretch", key=widget_key, config={"displayModeBar": show_modebar})
