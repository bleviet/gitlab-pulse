"""Milestone Burnup Chart Widget."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.theme import PALETTE, FONT_FAMILY, get_plotly_font_color


def milestone_burnup(
    df: pd.DataFrame,
    milestone_meta: pd.Series,
    config: dict[str, Any] | None = None
) -> None:
    """Render burn-up chart (Scope vs Completed) for a milestone.
    
    Args:
        df: DataFrame of issues in the milestone
        milestone_meta: Series containing milestone metadata (start_date, due_date)
        config: Optional config
            - key: widget key
            - height: chart height
    """
    config = config or {}
    height = config.get("height", 400)
    widget_key = config.get("key", "milestone_burnup")
    
    st.subheader("Burn-up Chart")

    # helper to ensure naive UTC
    def to_naive_utc(ts):
        if pd.isna(ts): return pd.NaT
        ts = pd.to_datetime(ts)
        if ts.tz is not None:
            ts = ts.tz_convert(None)
        return ts

    # We need a daily timeline from start date to today (or due date)
    start_date = to_naive_utc(milestone_meta.get("milestone_start_date"))
    # If no start date, pick the earliest creation date in the dataset
    if pd.isna(start_date):
        if not df.empty and "created_at" in df.columns:
            start_date = to_naive_utc(df["created_at"].min())
        else:
            start_date = pd.Timestamp.utcnow().replace(tzinfo=None) # fallback

    end_date = to_naive_utc(milestone_meta.get("milestone_due_date"))

    # Current time (Naive UTC)
    now = pd.Timestamp.utcnow().replace(tzinfo=None).normalize()

    if pd.isna(end_date):
        end_date = now + pd.Timedelta(days=30)

    # Generate timeline (Naive UTC)
    # Ensure start_date is not NaT if df empty and no meta
    if pd.isna(start_date):
         start_date = now
         
    timeline = pd.date_range(start=start_date, end=max(end_date, now), freq="D")

    # Pre-calculate counts per day
    # Created (Scope) -> Convert to Naive UTC
    if not df.empty and "created_at" in df.columns:
        df["created_date"] = pd.to_datetime(df["created_at"]).apply(to_naive_utc).dt.normalize()
        scope_counts = df.groupby("created_date").size().cumsum()
    else:
        scope_counts = pd.Series(dtype=int, index=pd.to_datetime([]))

    # Closed (Completed) -> Convert to Naive UTC
    if not df.empty and "closed_at" in df.columns:
        completed_df = df[df["state"] == "closed"].copy()
        if not completed_df.empty:
            completed_df["closed_date"] = pd.to_datetime(completed_df["closed_at"]).apply(to_naive_utc).dt.normalize()
            completed_counts = completed_df.groupby("closed_date").size().sort_index().cumsum()
        else:
            completed_counts = pd.Series(dtype=int, index=pd.to_datetime([]))
    else:
        completed_counts = pd.Series(dtype=int, index=pd.to_datetime([]))

    # Reindex series to timeline using ffill
    scope_series = scope_counts.reindex(timeline, method='ffill').fillna(0)
    completed_series = completed_counts.reindex(timeline, method='ffill').fillna(0)

    chart_df = pd.DataFrame({
        "Date": timeline,
        "Total Scope": scope_series.values,
        "Completed": completed_series.values,
    })

    # Plot
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=chart_df["Date"],
        y=chart_df["Total Scope"],
        mode='lines',
        name='Total Scope',
        line=dict(shape='hv', color=PALETTE["scope_line"], dash='dash')
    ))

    fig.add_trace(go.Scatter(
        x=chart_df["Date"],
        y=chart_df["Completed"],
        mode='lines',
        name='Completed',
        fill='tozeroy',
        line=dict(color=PALETTE["primary"])
    ))

    # Add vertical line for Today
    fig.add_vline(x=now.timestamp() * 1000, line_width=1, line_dash="dash", line_color="red", annotation_text="Today")

    # Add vertical line for Due Date
    if pd.notna(milestone_meta.get("milestone_due_date")):
        fig.add_vline(x=pd.to_datetime(milestone_meta["milestone_due_date"]).timestamp() * 1000, line_width=2, line_color="green", annotation_text="Due Date")

    fig.update_layout(
        height=height,
        xaxis_title="Date",
        yaxis_title="Issues",
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=1.1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT_FAMILY, color=get_plotly_font_color()),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(148, 163, 184, 0.18)"),
    )

    st.plotly_chart(fig, width="stretch", key=widget_key)
