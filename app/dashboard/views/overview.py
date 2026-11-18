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

from collections.abc import Callable

import pandas as pd
import streamlit as st

from app.dashboard.views.issue_data import overview_stages
from app.dashboard.views.issue_panel import (
    FULL_RERUN_KEY,
    render_issue_panel,
    sync_issue_state_from_query,
    write_query_state,
)
from app.dashboard.views.issue_search import inject_search_shortcut
from app.dashboard.views.overview_analytics import render_analytics_layout
from app.dashboard.views.overview_summary import build_summary, render_summary_bar
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


@st.fragment
def _issue_panel_fragment(
    df: pd.DataFrame,
    stages: list[str],
    toolbar: Callable[[], None] | None = None,
    show_filters: bool = True,
    lane_headers: bool = True,
) -> None:
    """Render the issue panel as a fragment.

    A click inside the panel (pager, pills, view switch) reruns only the
    panel, not the sidebar, the charts or the data load. The panel's filters
    are in the URL, so the URL state is written here too.
    """
    if st.session_state.pop(FULL_RERUN_KEY, False):
        # A sidebar filter was reset from a chip: the panel's data is stale.
        st.rerun()
    render_issue_panel(
        df, stages, toolbar=toolbar, show_filters=show_filters, lane_headers=lane_headers
    )
    write_query_state()


@st.fragment
def _analytics_fragment(
    df: pd.DataFrame,
    unique_df: pd.DataFrame,
    stages: list[str],
    timeline_source: pd.DataFrame,
    active_milestone: str | None,
) -> None:
    """Render the Analytics layout as a fragment.

    A chart click reruns the charts and the board below them, not the
    sidebar or the data load. The board is a fragment of its own inside
    (``_issue_panel_fragment``), so a click in it reruns only the board.
    """
    render_analytics_layout(
        unique_df,
        stages,
        timeline_source,
        active_milestone,
        # The charts above show the stages and the filters, so the board
        # keeps only the search and the view switch.
        board=lambda: _issue_panel_fragment(
            df, stages, show_filters=False, lane_headers=False
        ),
    )


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

    sync_issue_state_from_query()
    # A full run already satisfies a pending full-rerun request.
    st.session_state.pop(FULL_RERUN_KEY, None)
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
        _analytics_fragment(df, unique_df, stages, timeline_source, active_milestone)
    else:
        _render_release_rail(timeline_source, active_milestone)
        summary = build_summary(unique_df)
        _issue_panel_fragment(
            df,
            stages,
            toolbar=lambda: render_summary_bar(summary),
        )
    _write_layout_query(layout)
    inject_search_shortcut()
