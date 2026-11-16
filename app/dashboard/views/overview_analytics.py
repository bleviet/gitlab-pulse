"""Analytics layout of the Overview page.

The original chart grid (three rows of panels) for stepping back: the priority
donuts, the daily new-vs-closed line, the workflow-state bars, the release
timeline, open vs. closed issues and the quality signals. A click on a chart
segment filters the issue board below the grid and keeps the segment
highlighted (see ``issue_panel.apply_chart_selection``).
"""

from collections.abc import Callable
from typing import Any

import pandas as pd
import streamlit as st

from app.dashboard.engine import (
    GRID_COLUMNS,
    StreamlitGridCell,
    StreamlitGridRow,
    render_streamlit_grid,
)
from app.dashboard.theme import get_palette, get_plotly_font_color, with_alpha
from app.dashboard.views.issue_data import _build_overview_quality_signal_df
from app.dashboard.views.issue_panel import apply_chart_selection, chart_key
from app.dashboard.widgets import charts


def render_analytics_charts(
    unique_df: pd.DataFrame,
    stages: list[str],
    timeline_df: pd.DataFrame,
    active_milestone: str | None,
) -> None:
    """Render the three chart rows of the Analytics layout.

    Args:
        unique_df: Overview issues, one row per issue.
        stages: Stages with open issues, in workflow order.
        timeline_df: Issues before the milestone filter, for the timeline.
        active_milestone: Milestone picked in the sidebar or the timeline.
    """
    palette = get_palette()
    panel_label_color = with_alpha(get_plotly_font_color(), 0.72)

    def render_panel_header(title: str, meta: str | None = None) -> None:
        meta_html = (
            f"<span style='font-size:0.68rem; font-weight:700; letter-spacing:0.14em; "
            f"text-transform:uppercase; color:{palette['accent']};'>{meta}</span>"
            if meta
            else ""
        )
        st.markdown(
            "<div style='display:flex; align-items:center; justify-content:space-between; "
            "gap:0.75rem; margin-bottom:0.55rem;'>"
            f"<span style='font-size:0.78rem; font-weight:700; letter-spacing:0.12em; "
            f"text-transform:uppercase; color:{panel_label_color};'>{title}</span>"
            f"{meta_html}</div>",
            unsafe_allow_html=True,
        )

    def panel_cell(
        key: str,
        span: int,
        title: str,
        render_body: Callable[[], None],
        meta: str | None = None,
    ) -> StreamlitGridCell:
        def render_panel() -> None:
            with st.container(border=True):
                render_panel_header(title, meta=meta)
                render_body()

        return StreamlitGridCell(key=key, span=span, render=render_panel)

    def select(
        selection: dict[str, Any] | None,
        chart_id: str,
        stage_filter: str | None = None,
        state_filter: str | None = None,
    ) -> None:
        apply_chart_selection(selection, chart_id, stage_filter, state_filter)

    def open_priority() -> None:
        selection = charts.priority_donut(
            unique_df,
            config={
                "height": 200,
                "key": chart_key("analytics_priority_open", "open_donut"),
                "show_legend": False,
            },
        )
        select(selection, "open_donut", state_filter="opened")

    def closed_priority() -> None:
        selection = charts.priority_donut(
            unique_df,
            config={
                "height": 200,
                "key": chart_key("analytics_priority_closed", "closed_donut"),
                "show_legend": False,
                "state_filter": "closed",
                "center_text": "CLOSED<br>ISSUES",
            },
        )
        select(selection, "closed_donut", state_filter="closed")

    def velocity() -> None:
        selection = charts.daily_velocity_line(
            unique_df,
            config={"height": 200, "key": chart_key("analytics_velocity", "velocity_chart")},
        )
        select(selection, "velocity_chart")

    def workflow_state() -> None:
        if not stages:
            st.info("No stage data available.")
            return
        for index, (column, stage) in enumerate(zip(st.columns(len(stages)), stages, strict=True)):
            with column:
                st.markdown(
                    "<div style='text-align:center; font-size:0.75rem; font-weight:bold; "
                    f"color:#777; margin-bottom:-10px;'>{stage.upper()}</div>",
                    unsafe_allow_html=True,
                )
                selection = charts.priority_bar(
                    unique_df[unique_df["stage"] == stage],
                    config={
                        "height": 200,
                        "key": chart_key(f"analytics_stage_bar_{index}", f"stage_bar_{index}"),
                    },
                )
                select(selection, f"stage_bar_{index}", stage_filter=stage, state_filter="opened")

    def timeline() -> None:
        key_suffix = st.session_state.get("timeline_reset_counter", 0)
        selection = charts.milestone_timeline(
            timeline_df,
            config={
                "key": f"analytics_timeline_{key_suffix}",
                "height": 150,
                "highlight_milestone": active_milestone,
            },
        )
        points = (selection or {}).get("selection", {}).get("points") or []
        if points and len(points[0].get("customdata") or []) > 2:
            picked = points[0]["customdata"][2]
            if picked == active_milestone:
                st.session_state["overview_milestone_reset"] = True
            else:
                st.session_state["overview_milestone_pending"] = picked
            st.session_state["timeline_reset_counter"] = key_suffix + 1
            st.rerun()

    def issue_state() -> None:
        selection = charts.issue_state_bar(
            unique_df,
            config={"height": 150, "key": chart_key("analytics_issue_state", "issue_state_chart")},
        )
        select(selection, "issue_state_chart")

    def quality_signals() -> None:
        selection = charts.error_distribution(
            _build_overview_quality_signal_df(unique_df),
            config={
                "height": 150,
                "key": chart_key("analytics_quality_signals", "quality_signal_chart"),
            },
        )
        select(selection, "quality_signal_chart")

    rows = [
        StreamlitGridRow(
            cells=(
                panel_cell("analytics_open_priority", 3, "Open Issues by Priority", open_priority),
                panel_cell("analytics_closed_priority", 3, "Closed Issues by Priority", closed_priority),
                panel_cell("analytics_velocity", 6, "Daily New vs. Closed Issues", velocity),
            )
        ),
        StreamlitGridRow(
            cells=(
                panel_cell(
                    "analytics_workflow_state", GRID_COLUMNS, "Issues by Workflow State", workflow_state
                ),
            )
        ),
        StreamlitGridRow(
            cells=(
                panel_cell("analytics_timeline", 6, "Release Timeline", timeline, meta="Milestones"),
                panel_cell("analytics_issue_state", 3, "Open vs. Closed Issues", issue_state),
                panel_cell(
                    "analytics_quality_signals", 3, "Issue Quality Signals", quality_signals,
                    meta="Hints",
                ),
            )
        ),
    ]
    with st.container(key="overview_analytics"):
        for row in rows:
            render_streamlit_grid([row], total_columns=GRID_COLUMNS)
