"""Priority Donut Chart Widget."""

import math
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.theme import (
    get_active_theme_mode,
    get_palette,
    get_plotly_font_color,
    get_priority_colors,
    get_streamlit_theme_color,
    plotly_layout,
    with_alpha,
)

# ``customdata[0]`` of the donut's centre: the click selects all issues of the
# donut's state, not one priority.
ALL_ISSUES = "__all__"


def priority_donut(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render donut chart of open issues by priority.

    Args:
        df: DataFrame of issues
        config: Optional configuration; ``highlight`` names a priority whose
            slice stays fully coloured while the others are dimmed.
    """
    config = config or {}
    height = config.get("height", 250)
    widget_key = config.get("key", "priority_donut")
    center_text = config.get("center_text", "OPEN<br>ISSUES")
    show_legend = config.get("show_legend", True)

    if df.empty or "priority" not in df.columns:
        st.info("No priority data available.")
        return None

    state_filter = config.get("state_filter", "opened")
    if "state" in df.columns:
        if state_filter == "all":
            work_df = df.copy()
        else:
            work_df = df[df["state"] == state_filter].copy()
    else:
        work_df = df.copy()

    if work_df.empty:
        st.info(f"No {state_filter if state_filter != 'all' else ''} issues.")
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

    total_issues = priority_counts["Count"].sum()
    if total_issues == 0:
        return None

    palette = get_palette()
    
    colors_map = get_priority_colors()
    neutral = palette.get("neutral", "#95a5a6")

    if "priority_rank" in work_df.columns:
        ranks = work_df.groupby("priority")["priority_rank"].min().astype(float)
        priority_counts["Rank"] = priority_counts["Priority"].map(ranks)
    else:
        priority_counts["Rank"] = float("nan")
    priority_counts["IsUnset"] = priority_counts["Priority"] == "Unset"
    priority_counts = priority_counts.sort_values(["IsUnset", "Rank", "Priority"])
    
    labels = priority_counts["Priority"].tolist()
    values = priority_counts["Count"].tolist()
    colors = [colors_map.get(lbl, neutral) for lbl in labels]

    text_color = get_plotly_font_color()
    mode = get_active_theme_mode()
    bg_color = get_streamlit_theme_color("backgroundColor", "#050811" if mode == "dark" else "#f8f9fc")

    # Drawn on ordinary x/y axes, not as a pie: Plotly reports no click
    # selection for pie (or polar bar) slices, so a pie could not filter
    # anything. Each slice is a filled ring segment for the look; a grid of
    # invisible markers over the ring, and one large marker over the hole,
    # are the click targets. A selection carries ``[label, count]`` in
    # ``customdata``; the centre's label is ``ALL_ISSUES``.
    highlight = config.get("highlight")
    hole, step = 0.6, 2.0
    sweeps = [360.0 * value / total_issues for value in values]
    starts = [sum(sweeps[:index]) for index in range(len(sweeps))]

    def ring_point(angle: float, radius: float) -> tuple[float, float]:
        # Clockwise from 12 o'clock, like the pie it replaces.
        radians = math.radians(90 - angle)
        return radius * math.cos(radians), radius * math.sin(radians)

    fig = go.Figure()
    for label, color, start, sweep in zip(labels, colors, starts, sweeps, strict=True):
        angles = [start + sweep * i / max(int(sweep / step), 1) for i in range(max(int(sweep / step), 1) + 1)]
        outline = [ring_point(angle, 1.0) for angle in angles] + [
            ring_point(angle, hole) for angle in reversed(angles)
        ]
        dimmed = highlight is not None and label != highlight
        fig.add_trace(go.Scatter(
            x=[x for x, _ in outline] + [outline[0][0]],
            y=[y for _, y in outline] + [outline[0][1]],
            fill="toself",
            fillcolor=with_alpha(color, 0.3) if dimmed else color,
            line=dict(color=bg_color, width=2),
            mode="lines",
            hoverinfo="skip",
            name=label,
            showlegend=show_legend,
        ))

    targets: list[tuple[float, float, str, int]] = []
    for label, value, start, sweep in zip(labels, values, starts, sweeps, strict=True):
        count = max(int(sweep / 6), 1)
        for i in range(count):
            angle = start + sweep * (i + 0.5) / count
            for radius in (0.7, 0.9):
                x, y = ring_point(angle, radius)
                targets.append((x, y, label, value))
    fig.add_trace(go.Scatter(
        x=[x for x, _, _, _ in targets] + [0.0],
        y=[y for _, y, _, _ in targets] + [0.0],
        mode="markers",
        marker=dict(
            size=[18] * len(targets) + [int(height * 0.42)],
            color="rgba(0,0,0,0)",
        ),
        customdata=[[label, value] for _, _, label, value in targets]
        + [[ALL_ISSUES, total_issues]],
        hovertemplate="%{customdata[0]}: %{customdata[1]}<extra></extra>",
        showlegend=False,
    ))
    # Slice values, at the middle of each segment.
    middles = [ring_point(start + sweep / 2, (1 + hole) / 2) for start, sweep in zip(starts, sweeps, strict=True)]
    fig.add_trace(go.Scatter(
        x=[x for x, _ in middles],
        y=[y for _, y in middles],
        mode="text",
        text=[str(value) if sweep >= 18 else "" for value, sweep in zip(values, sweeps, strict=True)],
        textfont=dict(color="#ffffff", size=12),
        hoverinfo="skip",
        showlegend=False,
    ))
    # ``constrain="domain"`` keeps the ring round and centred in the panel.
    fig.update_xaxes(visible=False, range=[-1.08, 1.08], fixedrange=True, constrain="domain")
    fig.update_yaxes(visible=False, range=[-1.08, 1.08], fixedrange=True, scaleanchor="x", scaleratio=1)

    fig.add_annotation(
        text=f"<b style='font-size:28px; color:{text_color};'>{total_issues}</b><br><span style='font-size:12px; color:{text_color};'>{center_text}</span>",
        x=0, y=0,
        xref="x", yref="y",
        font=dict(family="Inter, sans-serif"),
        showarrow=False,
        xanchor="center",
        yanchor="middle",
    )

    fig.update_layout(
        **plotly_layout(
            height=height,
            margin=dict(l=0, r=0 if not show_legend else 20, t=10, b=10),
            legend_pos="right" if show_legend else "none",
        ),
    )
    
    fig.update_layout(
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.0
        )
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
