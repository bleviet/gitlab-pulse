"""Priority Donut Chart Widget."""

import math
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.figure_cache import cache_figure, theme_key
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


def _value_label(
    value: int, start: float, sweep: float, height: int, hole: float
) -> tuple[float, int] | None:
    """Place a slice value inside its ring segment, or hide it.

    The label is modelled as a horizontal box ``0.6 em`` wide per digit and
    ``1.2 em`` tall (measured from a rendered chart), 1 px clear of the ring
    edges and of the 2 px slice separators. Nine positions along the slice are
    tried with sizes from 12 down to 8 px; the largest size wins, then the
    position closest to the slice middle.

    Args:
        value: The slice's issue count.
        start: Slice start angle in degrees, clockwise from 12 o'clock.
        sweep: Slice angular width in degrees.
        height: Chart height in px (the axes span +-1.08 within 10 px margins).
        hole: Inner radius as a fraction of the outer radius.

    Returns:
        ``(angle, font size)`` of the label centre, or ``None`` when no
        position fits at 8 px (the hover still shows the value).
    """
    outer = (height - 20) / 2.16
    inner = hole * outer
    pad = math.degrees(1 / inner)
    middle = start + sweep / 2
    text_length = len(str(value))
    best: tuple[int, float, float] | None = None
    for i in range(9):
        angle = start + sweep * (i + 0.5) / 9
        cx = (outer + inner) / 2 * math.sin(math.radians(angle))
        cy = (outer + inner) / 2 * math.cos(math.radians(angle))
        for size in range(12, 7, -1):
            half_w, half_h = 0.3 * size * text_length, 0.6 * size
            nearest = math.hypot(
                max(abs(cx) - half_w, 0.0), max(abs(cy) - half_h, 0.0)
            )
            corners = [
                (cx + dx, cy + dy) for dx in (-half_w, half_w) for dy in (-half_h, half_h)
            ]
            offsets = [
                (math.degrees(math.atan2(x, y)) - middle + 180) % 360 - 180
                for x, y in corners
            ]
            if (
                nearest >= inner + 1
                and all(math.hypot(x, y) <= outer - 1 for x, y in corners)
                and all(abs(offset) <= sweep / 2 - pad for offset in offsets)
            ):
                distance = abs(angle - middle)
                if best is None or size > best[0] or (
                    size == best[0] and distance < best[1]
                ):
                    best = (size, distance, angle)
                break
    return None if best is None else (best[2], best[0])


@cache_figure
def _figure(
    labels: list[str],
    values: list[int],
    colors: list[str],
    total_issues: int,
    highlight: str | None,
    height: int,
    center_text: str,
    show_legend: bool,
    theme_key: tuple[object, ...],
) -> go.Figure:
    """Build the donut figure (cached; see ``figure_cache``)."""
    text_color = get_plotly_font_color()
    mode = get_active_theme_mode()
    bg_color = get_streamlit_theme_color("backgroundColor", "#050811" if mode == "dark" else "#f8f9fc")

    # Drawn on ordinary x/y axes, not as a pie: Plotly reports no click
    # selection for pie (or polar bar) slices, so a pie could not filter
    # anything. Each slice is a filled ring segment for the look; a grid of
    # invisible markers over the ring, and one large marker over the hole,
    # are the click targets. A selection carries ``[label, count]`` in
    # ``customdata``; the centre's label is ``ALL_ISSUES``.
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
    # Slice values, inside each segment where they fit.
    labels_at = [
        _value_label(value, start, sweep, height, hole)
        for value, start, sweep in zip(values, starts, sweeps, strict=True)
    ]
    points = [
        ring_point(placed[0] if placed else start, (1 + hole) / 2)
        for placed, start in zip(labels_at, starts, strict=True)
    ]
    fig.add_trace(go.Scatter(
        x=[x for x, _ in points],
        y=[y for _, y in points],
        mode="text",
        text=[str(value) if placed else "" for value, placed in zip(values, labels_at, strict=True)],
        textfont=dict(color="#ffffff", size=[placed[1] if placed else 8 for placed in labels_at]),
        hoverinfo="skip",
        showlegend=False,
    ))
    # ``constrain="domain"`` keeps the ring round and centred in the panel.
    fig.update_xaxes(visible=False, range=[-1.08, 1.08], fixedrange=True, constrain="domain")
    fig.update_yaxes(visible=False, range=[-1.08, 1.08], fixedrange=True, scaleanchor="x", scaleratio=1)

    # The hole shrinks with the chart, so the centre text does too.
    total_size = min(28, round(height * 0.14))
    caption_size = min(12, round(height * 0.07))
    fig.add_annotation(
        text=f"<b style='font-size:{total_size}px; color:{text_color};'>{total_issues}</b><br><span style='font-size:{caption_size}px; color:{text_color};'>{center_text}</span>",
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
    return fig


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
    columns = [name for name in ("priority", "priority_rank") if name in df.columns]
    if "state" in df.columns:
        if state_filter == "all":
            work_df = df[columns].copy()
        else:
            work_df = df.loc[df["state"] == state_filter, columns].copy()
    else:
        work_df = df[columns].copy()

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

    fig = _figure(
        labels,
        values,
        colors,
        int(total_issues),
        config.get("highlight"),
        height,
        center_text,
        show_legend,
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
