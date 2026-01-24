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
from app.dashboard.data_loader import load_milestones
from app.dashboard.widgets import kpis, charts, tables
from app.dashboard.components import style_metric_cards


def render_release_view(df: pd.DataFrame) -> None:
    """Render the release management dashboard.

    Args:
        df: DataFrame containing all issues
    """
    st.header("Release Management")

    # Build milestone data from issues (same source as dropdown)
    # This ensures timeline shows all milestones that have issues
    if "milestone_id" in df.columns and not df["milestone_id"].isnull().all():
        milestone_df = df[df["milestone_id"].notna()].copy()
        ms_agg = milestone_df.groupby("milestone").agg({
            "milestone_id": "first",
            "milestone_due_date": "first",
            "milestone_start_date": "first",
            "iid": "count",  # Use iid for count to avoid column name conflict
            "state": lambda x: "closed" if (x == "closed").all() else "active"
        }).reset_index()
        ms_agg = ms_agg.rename(columns={
            "milestone": "title",
            "milestone_id": "id",
            "milestone_due_date": "due_date",
            "milestone_start_date": "start_date",
            "iid": "issue_count",
            "state": "milestone_state"
        })
        # Use milestone_state for timeline status
        ms_agg["state"] = ms_agg["milestone_state"]
    else:
        ms_agg = pd.DataFrame()

    # Milestone Timeline Section (Collapsible, collapsed by default)
    if not ms_agg.empty:
        with st.expander("📅 Milestone Timeline", expanded=True):
            timeline_selection = charts.milestone_timeline(ms_agg, df, config={"key": "release_timeline"})

            # Handle selection from timeline
            if timeline_selection and timeline_selection.get("selection", {}).get("points"):
                points = timeline_selection["selection"]["points"]
                if points:
                    # We added title as customdata[2]
                    try:
                        selected_milestone = points[0]["customdata"][2]
                        st.session_state["release_milestone_selector"] = selected_milestone
                        # Rerun is handled by st.plotly_chart(on_select="rerun")
                    except (IndexError, KeyError):
                        pass

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
                "height": 800,
                "columns": ["web_url", "title", "issue_type", "state", "assignee", "priority"]
            }
        )







