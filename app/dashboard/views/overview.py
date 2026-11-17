"""Overview Page (Value Stream) for Layer 3 Dashboard.

Two layouts share one issue board, one filter and one URL format:

- **Compact** (default), for daily triage: the board starts high on the screen.
  Above it sits only a thin release rail; the summary pills share the board's
  toolbar row, and the workflow state is shown in the lane headers.
- **Analytics**, for stepping back: the original chart grid above the board
  (see ``overview_analytics``). A chart click filters the board.

A switch at the top right of the page, in Streamlit's header bar, changes the
layout; the choice is kept in the session and in the URL (``?view=analytics``).
"""

import pandas as pd
import streamlit as st

from app.dashboard.views.issue_data import overview_stages
from app.dashboard.views.issue_panel import (
    finish_issue_state,
    render_issue_panel,
    sync_issue_state_from_query,
)
from app.dashboard.views.overview_analytics import render_analytics_layout
from app.dashboard.views.overview_summary import render_summary_bar
from app.dashboard.views.pinned_header import inject_pinned_header_script
from app.dashboard.widgets import charts

_LAYOUTS = {"Compact": ":material/view_agenda:", "Analytics": ":material/insert_chart:"}
_LAYOUT_QUERY_KEY = "view"


def _current_layout() -> str:
    """Return the Overview layout; on a fresh session, take it from the URL."""
    if "overview_layout" not in st.session_state:
        from_url = str(st.query_params.get(_LAYOUT_QUERY_KEY, "")).strip().lower()
        st.session_state["overview_layout"] = "Analytics" if from_url == "analytics" else "Compact"
    return str(st.session_state["overview_layout"])


def _on_layout_change() -> None:
    chosen = st.session_state.get("overview_layout_choice")
    if chosen in _LAYOUTS:
        st.session_state["overview_layout"] = chosen


def _layout_label(layout: str) -> str:
    return f"{_LAYOUTS[layout]} {layout}"


def _render_layout_switch() -> None:
    """Compact/Analytics switch, pinned into the header bar at the top right.

    The header bar is otherwise nearly empty, so the switch costs no height and
    stays in the same place in both layouts (see the theme CSS).
    """
    # Reflect the current layout even after it was set from the URL.
    st.session_state["overview_layout_choice"] = st.session_state["overview_layout"]
    with st.container(key="overview_layout_bar"):
        st.segmented_control(
            "Overview layout",
            list(_LAYOUTS),
            format_func=_layout_label,
            key="overview_layout_choice",
            label_visibility="collapsed",
            on_change=_on_layout_change,
            help="Compact: board first. Analytics: the full charts above the board.",
        )


def _write_layout_query(layout: str) -> None:
    if layout == "Analytics":
        if st.query_params.get(_LAYOUT_QUERY_KEY) != "analytics":
            st.query_params[_LAYOUT_QUERY_KEY] = "analytics"
    elif _LAYOUT_QUERY_KEY in st.query_params:
        del st.query_params[_LAYOUT_QUERY_KEY]


def _render_release_rail(timeline_source: pd.DataFrame, active_milestone: str | None) -> None:
    with st.container(key="overview_releases"):
        key_suffix = st.session_state.get("timeline_reset_counter", 0)
        selection = charts.milestone_timeline(
            timeline_source,
            config={
                "key": f"overview_timeline_{key_suffix}",
                "height": 72,
                "style": "rail",
                "title": "RELEASES",
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


def render_overview(
    df: pd.DataFrame,
    quality_df: pd.DataFrame | None = None,
    stage_descriptions: dict[str, str] | None = None,
    timeline_df: pd.DataFrame | None = None,
    highlight_milestone: str | None = None,
) -> None:
    """Render the Overview (Flow) page in the Compact or Analytics layout.

    Args:
        df: Filtered DataFrame with valid issues (milestone filter applied)
        quality_df: Optional quality-hint dataframe for supporting widgets
        stage_descriptions: Optional mapping of stage names to description strings
        timeline_df: Unfiltered DataFrame for the milestone timeline
        highlight_milestone: Active milestone name to highlight in the timeline
    """
    if df.empty:
        st.warning("No data available.")
        return

    sync_issue_state_from_query(df)
    layout = _current_layout()
    _render_layout_switch()
    inject_pinned_header_script()

    unique_df = df.drop_duplicates(subset=["id"]) if "id" in df.columns else df
    stages = overview_stages(unique_df)
    timeline_source = timeline_df if timeline_df is not None else df
    if "id" in timeline_source.columns:
        timeline_source = timeline_source.drop_duplicates(subset=["id"])
    active_milestone = (
        highlight_milestone if highlight_milestone and highlight_milestone != "All" else None
    )

    if layout == "Analytics":
        render_analytics_layout(
            unique_df,
            stages,
            timeline_source,
            active_milestone,
            # The charts above show the stages and the filters, so the board
            # keeps only the search and the view switch.
            board=lambda: render_issue_panel(
                df, stages, show_filters=False, lane_headers=False
            ),
        )
    else:
        _render_release_rail(timeline_source, active_milestone)
        render_issue_panel(
            df,
            stages,
            toolbar=lambda: render_summary_bar(unique_df),
        )
    _write_layout_query(layout)
    finish_issue_state(df)
