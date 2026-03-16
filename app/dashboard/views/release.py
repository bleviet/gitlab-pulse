"""Release management dashboard view.

Visualizes release readiness, burn-up charts, and scope management.
Refactored to use Widget Registry where applicable.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.shared.schemas import AnalyticsIssue
from app.dashboard.utils import sort_hierarchy
from app.dashboard.widgets import kpis, charts, tables
from app.dashboard.components import style_metric_cards


def render_release_view(df: pd.DataFrame) -> None:
    """Render the release management dashboard.

    Args:
        df: DataFrame containing all issues
    """


    # Milestone Timeline Section
    if "milestone_id" in df.columns and not df["milestone_id"].isnull().all():
        _active_ms = st.session_state.get("release_milestone_selector")
        _active_ms_highlight = _active_ms if _active_ms and _active_ms != "All" else None
        with st.expander("📅 Milestone Timeline", expanded=True):
            timeline_selection = charts.milestone_timeline(
                df,
                config={
                    "key": "release_timeline",
                    "highlight_milestone": _active_ms_highlight,
                },
            )
            points = (timeline_selection or {}).get("selection", {}).get("points")
            prev_ms = st.session_state.get("release_last_timeline_ms", "")
            skip_reset = st.session_state.pop("release_timeline_skip_reset", False)
            if points:
                try:
                    selected_milestone = points[0]["customdata"][2]
                    if selected_milestone != prev_ms:
                        st.session_state["release_last_timeline_ms"] = selected_milestone
                        st.session_state["release_milestone_selector"] = selected_milestone
                        st.session_state["release_timeline_skip_reset"] = True
                        st.rerun()
                except (IndexError, KeyError):
                    pass
            elif isinstance(points, list) and prev_ms and not skip_reset:
                # Only reset if the active milestone still matches what the timeline
                # last set. An independent sidebar change also produces empty points
                # (figure redraws) — guard against that false positive.
                if _active_ms_highlight == prev_ms:
                    st.session_state["release_last_timeline_ms"] = ""
                    st.session_state.pop("release_milestone_selector", None)
                    st.session_state["release_timeline_skip_reset"] = True
                    st.rerun()

    # 1. Milestone Selection
    if "milestone_id" not in df.columns or df["milestone_id"].isnull().all():
        st.warning("No issues with milestones found. Assign issues to milestones to see release scope.")
        return

    # Filter to items with milestones
    milestone_df = df[df["milestone_id"].notna()].copy()

    # Get unique milestones sorted by due date (if available) or name
    # We want a nice label like "Title (Due: Date)"
    ms_agg = milestone_df.groupby("milestone").agg({
        "milestone_id": "first",
        "milestone_due_date": "first",
        "milestone_start_date": "first",
        "id": "count"
    }).reset_index()

    # Sort by due date desc
    if "milestone_due_date" in ms_agg.columns:
        ms_agg = ms_agg.sort_values("milestone_due_date", ascending=False)

    # Create selection map
    ms_map = {row["milestone"]: row["milestone_id"] for _, row in ms_agg.iterrows()}
    allowed_milestones = list(ms_map.keys())

    if not allowed_milestones:
        st.info("No milestones found.")
        return

    # Determine active milestone:
    # 1. Timeline click (session_state)
    # 2. Default to first in list

    selected_milestone_name = None

    # Check session state override from timeline
    if "release_milestone_selector" in st.session_state:
        candidate = st.session_state["release_milestone_selector"]
        if candidate in allowed_milestones:
            selected_milestone_name = candidate

    # Fallback to first available
    if not selected_milestone_name:
        selected_milestone_name = allowed_milestones[0]
        # Sync back to session state so interactions are consistent
        st.session_state["release_milestone_selector"] = selected_milestone_name

    selected_ms_id = ms_map[selected_milestone_name]

    # Filter data for selected milestone
    ms_data = milestone_df[milestone_df["milestone_id"] == selected_ms_id].copy()

    # Get milestone metadata
    ms_meta = ms_agg[ms_agg["milestone_id"] == selected_ms_id].iloc[0]

    # 2. Release KPIs
    total_issues = len(ms_data)
    closed_issues = len(ms_data[ms_data["state"] == "closed"])
    pct_complete = (closed_issues / total_issues * 100) if total_issues > 0 else 0

    # Calculate days remaining
    days_remaining = "N/A"
    status_color = "off"
    if pd.notna(ms_meta.get("milestone_due_date")):
        due_date = pd.to_datetime(ms_meta["milestone_due_date"])
        # Normalize timezone: some GitLab instances return tz-naive, others tz-aware
        if due_date.tz is None:
            due_date = due_date.tz_localize("UTC")
        now = pd.Timestamp.now(tz="UTC")
        remaining = (due_date - now).days
        days_remaining = f"{remaining} days"

        if remaining < 0 and pct_complete < 100:
            status_color = "inverse" # Late
        elif remaining < 7 and pct_complete < 80:
            status_color = "normal" # At Risk (using normal as warning-ish?)

    # Apply Bento Grid Style
    from app.dashboard.components import style_metric_cards
    style_metric_cards()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Milestone", selected_milestone_name, help="Selected release scope")
    col2.metric("Progress", f"{pct_complete:.1f}%", f"{closed_issues}/{total_issues} Issues")
    col3.metric("Days Remaining", days_remaining)
    col4.metric("Total Issues", total_issues, help="Total issues in milestone")

    # 3. Burn-up Chart (Collapsible)
    with st.expander("📈 Burn-up Chart", expanded=True):
        charts.milestone_burnup(ms_data, ms_meta, config={"key": "release_burnup"})

    # 4. Scope Table (Collapsible)
    with st.expander("📋 Release Scope", expanded=True):
        # Use shared grid widget which handles hierarchy and filters
        tables.issue_detail_grid(
            ms_data,
            config={
                "key": "release_scope_grid",
                "columns": ["web_url", "title", "issue_type", "state", "assignee", "priority"]
            }
        )







