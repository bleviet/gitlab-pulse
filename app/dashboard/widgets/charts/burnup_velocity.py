"""Burnup Velocity Chart Widget."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from app.dashboard.theme import get_palette, get_plotly_grid_color, plotly_layout


def burnup_velocity(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> None:
    """Render faceted cumulative flow diagram (burn-up chart).

    Args:
        df: DataFrame of issues
        config: Optional configuration with keys:
            - height: chart height in pixels
    """
    config = config or {}
    height = config.get("height", 600)

    if df.empty:
        st.info("No data for cumulative flow chart")
        return

    # Prepare weekly data (remove timezone before period conversion)
    df_copy = df.copy()
    df_copy["created_week"] = df_copy["created_at"].dt.tz_localize(None).dt.to_period("W").dt.start_time

    # Panel configuration
    palette = get_palette()
    panels = [
        {"type": "Feature", "title": "Features (Value Flow)", "fill": palette["burnup_feature_fill"], "area": palette["burnup_feature_area"]},
        {"type": "Bug", "title": "Bugs (Failure Demand)", "fill": palette["burnup_bug_fill"], "area": palette["burnup_bug_area"]},
        {"type": "Task", "title": "Tasks (Maintenance)", "fill": palette["burnup_task_fill"], "area": palette["burnup_task_area"]},
    ]

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=[p["title"] for p in panels],
    )

    all_weeks = sorted(df_copy["created_week"].unique())

    for i, panel in enumerate(panels, start=1):
        type_df = df_copy[df_copy["issue_type"] == panel["type"]].copy()

        if type_df.empty:
            fig.add_trace(go.Scatter(
                x=all_weeks, y=[0] * len(all_weeks),
                mode="lines", name=f'{panel["type"]} Created',
                line=dict(color=panel["fill"], width=2),
                showlegend=False,
            ), row=i, col=1)
            continue

        # Calculate cumulative created
        weekly_created = type_df.groupby("created_week").size().reindex(all_weeks, fill_value=0).cumsum()

        # Calculate cumulative closed
        closed_df = type_df[type_df["closed_at"].notna()].copy()
        if not closed_df.empty:
            closed_df["closed_week"] = closed_df["closed_at"].dt.tz_localize(None).dt.to_period("W").dt.start_time
            weekly_closed = closed_df.groupby("closed_week").size().reindex(all_weeks, fill_value=0).cumsum()
        else:
            weekly_closed = pd.Series([0] * len(all_weeks), index=all_weeks)

        # Total Created line
        fig.add_trace(go.Scatter(
            x=weekly_created.index,
            y=weekly_created.values,
            mode="lines",
            name=f'{panel["type"]} Created',
            line=dict(color=panel["fill"], width=2),
            fill="tozeroy",
            fillcolor=panel["area"],
            showlegend=False,
            hovertemplate="Created: %{y}<extra></extra>",
        ), row=i, col=1)

        # Total Closed filled area
        fig.add_trace(go.Scatter(
            x=weekly_closed.index,
            y=weekly_closed.values,
            mode="lines",
            name=f'{panel["type"]} Closed',
            line=dict(color=panel["fill"], width=2),
            fill="tozeroy",
            fillcolor=panel["fill"],
            showlegend=False,
            hovertemplate="Closed: %{y}<extra></extra>",
        ), row=i, col=1)

    fig.update_layout(
        **plotly_layout(
            height=height,
            margin=dict(l=0, r=0, t=50, b=0),
            hovermode="x unified"
        )
    )

    for i in range(1, 4):
        fig.update_yaxes(
            showgrid=True,
            gridcolor=get_plotly_grid_color(),
            zeroline=False,
            row=i, col=1,
        )
        fig.update_xaxes(
            showgrid=False,
            showticklabels=(i == 3),
            row=i, col=1,
        )

    st.plotly_chart(fig, width="stretch", key=config.get("key", "burnup_velocity_chart") if config else None)
