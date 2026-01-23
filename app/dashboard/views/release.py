"""Release management dashboard view.

Visualizes release readiness, burn-up charts, and scope management.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.shared.schemas import AnalyticsIssue
from app.dashboard.utils import sort_hierarchy
from app.dashboard.data_loader import load_milestones


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
            _render_milestone_timeline(ms_agg, df)

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

    selected_milestone_name = st.selectbox("Select Milestone", allowed_milestones)
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
    col1.metric("Progress", f"{pct_complete:.1f}%", f"{closed_issues}/{total_issues} Issues")
    col2.metric("Days Remaining", days_remaining)
    col3.metric("Scope", total_issues, help="Total issues in milestone")

    # 3. Burn-up Chart (Collapsible)
    with st.expander("📈 Burn-up Chart", expanded=True):
        _render_burnup_chart(ms_data, ms_meta)

    # 4. Scope Table (Collapsible)
    with st.expander("📋 Release Scope", expanded=True):
        # Format for display
        display_df = ms_data.copy()

        # Sort hierarchy if available
        if "parent_id" in display_df.columns:
            display_df = sort_hierarchy(display_df, parent_col="parent_id", id_col="iid", title_col="title")
        else:
            display_df = display_df.sort_values(["state", "updated_at"], ascending=[True, False])

        # Link
        display_df = display_df.rename(columns={
            "web_url": "IID",
            "title": "Title",
            "state": "State",
            "assignee": "Assignee",
            "issue_type": "Type"
        })

        st.dataframe(
            display_df,
            column_config={
                "IID": st.column_config.LinkColumn(
                    "IID",
                    display_text=r"/(?:issues|work_items)/(\d+)$",
                    width="small"
                ),
                "Title": st.column_config.TextColumn("Title", width="large"),
                "State": st.column_config.TextColumn("State", width="small"),
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Assignee": st.column_config.TextColumn("Assignee", width="medium"),
            },
            column_order=["IID", "Title", "Type", "State", "Assignee"],
            width="stretch",
            height=800,
            hide_index=True,
        )


def _render_burnup_chart(df: pd.DataFrame, meta: pd.Series):
    """Render burn-up chart (Scope vs Completed)."""
    st.subheader("Burn-up Chart")

    # helper to ensure naive UTC
    def to_naive_utc(ts):
        if pd.isna(ts): return pd.NaT
        ts = pd.to_datetime(ts)
        if ts.tz is not None:
            ts = ts.tz_convert(None)
        return ts

    # We need a daily timeline from start date to today (or due date)
    start_date = to_naive_utc(meta.get("milestone_start_date"))
    # If no start date, pick the earliest creation date in the dataset
    if pd.isna(start_date):
        if not df.empty:
            start_date = to_naive_utc(df["created_at"].min())
        else:
            start_date = pd.Timestamp.utcnow().replace(tzinfo=None) # fallback

    end_date = to_naive_utc(meta.get("milestone_due_date"))

    # Current time (Naive UTC)
    now = pd.Timestamp.utcnow().replace(tzinfo=None).normalize()

    if pd.isna(end_date):
        end_date = now + pd.Timedelta(days=30)

    # Generate timeline (Naive UTC)
    timeline = pd.date_range(start=start_date, end=max(end_date, now), freq="D")

    # Pre-calculate counts per day
    # Created (Scope) -> Convert to Naive UTC
    if not df.empty:
        df["created_date"] = pd.to_datetime(df["created_at"]).apply(to_naive_utc).dt.normalize()
        scope_counts = df.groupby("created_date").size().cumsum()
    else:
        scope_counts = pd.Series(dtype=int, index=pd.to_datetime([]))

    # Closed (Completed) -> Convert to Naive UTC
    completed_df = df[df["state"] == "closed"].copy()
    if not completed_df.empty:
        completed_df["closed_date"] = pd.to_datetime(completed_df["closed_at"]).apply(to_naive_utc).dt.normalize()
        completed_counts = completed_df.groupby("closed_date").size().sort_index().cumsum()
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

    # Ideal line? (Start 0 to Total Scope at Due Date)
    # Only if we have strict dates

    fig.add_trace(go.Scatter(
        x=chart_df["Date"],
        y=chart_df["Total Scope"],
        mode='lines',
        name='Total Scope',
        line=dict(shape='hv', color='gray', dash='dash')
    ))

    fig.add_trace(go.Scatter(
        x=chart_df["Date"],
        y=chart_df["Completed"],
        mode='lines',
        name='Completed',
        fill='tozeroy',
        line=dict(color='#3B82F6')
    ))

    # Add vertical line for Today
    fig.add_vline(x=now.timestamp() * 1000, line_width=1, line_dash="dash", line_color="red", annotation_text="Today")

    # Add vertical line for Due Date
    if pd.notna(meta.get("milestone_due_date")):
        fig.add_vline(x=pd.to_datetime(meta["milestone_due_date"]).timestamp() * 1000, line_width=2, line_color="green", annotation_text="Due Date")

    fig.update_layout(
        height=400,
        xaxis_title="Date",
        yaxis_title="Issues",
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", y=1.1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif"),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(128, 128, 128, 0.2)"),
    )

    st.plotly_chart(fig, width="stretch")


def _render_milestone_timeline(milestones_df: pd.DataFrame, issues_df: pd.DataFrame) -> None:
    """Render milestone timeline as a scatter plot with markers.

    Color scheme:
    - Purple: Closed milestone with all issues resolved
    - Red: Closed milestone with unresolved issues remaining
    - Green: Open milestone, due date not yet reached
    - Orange: Open milestone, due date already passed (overdue)
    """
    if milestones_df.empty:
        st.info("No milestones to display.")
        return

    now = pd.Timestamp.now(tz="UTC")
    display_df = milestones_df.copy()

    # Calculate issue completion per milestone
    milestone_issue_stats = {}
    if not issues_df.empty and "milestone_id" in issues_df.columns:
        for ms_id in display_df["id"].unique():
            ms_issues = issues_df[issues_df["milestone_id"] == ms_id]
            total = len(ms_issues)
            closed = len(ms_issues[ms_issues["state"] == "closed"])
            milestone_issue_stats[ms_id] = {"total": total, "closed": closed}

    # Prepare scatter data
    scatter_data = []
    for _, row in display_df.iterrows():
        ms_id = row["id"]
        title = row.get("title", f"Milestone {ms_id}")
        state = row.get("state", "active")

        # Get due date (primary) or start date as fallback
        due_date = row.get("due_date")
        start_date = row.get("start_date")

        # Skip milestones without a due date
        if pd.isna(due_date):
            continue

        # Normalize timezones
        if pd.notna(due_date):
            due_date = pd.to_datetime(due_date)
            if due_date.tz is None:
                due_date = due_date.tz_localize("UTC")
        if pd.notna(start_date):
            start_date = pd.to_datetime(start_date)
            if start_date.tz is None:
                start_date = start_date.tz_localize("UTC")

        # Use due date as marker position
        marker_date = due_date

        # Determine status and color
        stats = milestone_issue_stats.get(ms_id, {"total": 0, "closed": 0})
        all_issues_closed = stats["total"] == 0 or stats["closed"] == stats["total"]

        if state == "closed":
            if all_issues_closed:
                color = "#9333EA"  # Purple-600
                status = "Complete"
            else:
                color = "#DC2626"  # Red-600
                status = "Incomplete"
        else:
            if pd.notna(due_date) and due_date < now:
                color = "#EA580C"  # Orange-600
                status = "Overdue"
            else:
                color = "#16A34A"  # Green-600
                status = "On Track"

        # Format date for display
        date_str = marker_date.strftime("%Y-%m-%d") if pd.notna(marker_date) else "No date"

        scatter_data.append({
            "date": marker_date,
            "date_str": date_str,
            "title": title,
            "status": status,
            "color": color,
            "issues": f"{stats['closed']}/{stats['total']}",
        })

    if not scatter_data:
        st.info("No milestones to display.")
        return

    chart_df = pd.DataFrame(scatter_data)

    # Sort by date for staggering calculation
    chart_df = chart_df.sort_values("date").reset_index(drop=True)

    # Assign staggered y-positions to avoid overlapping markers
    # Group by date and assign alternating rows
    date_counts = {}
    y_positions = []
    for _, row in chart_df.iterrows():
        date_val = row["date"]
        if pd.notna(date_val):
            # Convert to string key to avoid timestamp issues
            date_key = str(pd.to_datetime(date_val).date())
        else:
            date_key = "nodate"
        count = date_counts.get(date_key, 0)
        y_positions.append(float(count % 3))  # Max 3 rows, use float
        date_counts[date_key] = count + 1

    chart_df["y_pos"] = y_positions

    # Create scatter plot
    fig = go.Figure()

    # Add traces for each status (for legend)
    status_colors = {
        "Complete": "#9333EA",
        "Incomplete": "#DC2626",
        "On Track": "#16A34A",
        "Overdue": "#EA580C",
    }

    for status, color in status_colors.items():
        status_df = chart_df[chart_df["status"] == status]
        if not status_df.empty:
            fig.add_trace(go.Scatter(
                x=status_df["date"],
                y=status_df["y_pos"],
                mode="markers+text",
                name=status,
                marker=dict(
                    size=16,
                    color=color,
                    symbol="diamond",
                    line=dict(width=1, color="white"),
                ),
                text=status_df["title"],
                textposition="top center",
                textfont=dict(size=10),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Due: %{customdata[0]}<br>"
                    "Issues: %{customdata[1]}<br>"
                    "Status: " + status +
                    "<extra></extra>"
                ),
                customdata=list(zip(status_df["date_str"], status_df["issues"])),
            ))

    # Add vertical line for today using shape (avoids annotation arithmetic issues)
    today_str = now.strftime("%Y-%m-%d")
    fig.add_shape(
        type="line",
        x0=today_str, x1=today_str,
        y0=0, y1=1,
        yref="paper",
        line=dict(width=2, dash="dash", color="rgba(128, 128, 128, 0.8)"),
    )
    fig.add_annotation(
        x=today_str,
        y=1.05,
        yref="paper",
        text="Today",
        showarrow=False,
        font=dict(size=10),
    )

    # Style for dark/light mode compatibility
    fig.update_layout(
        height=200,  # Fixed compact height
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif"),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(128, 128, 128, 0.2)",
            title="",
            type="date",
            # Default view: 9 months before, 3 months after today
            range=[
                (now - pd.Timedelta(days=270)).strftime("%Y-%m-%d"),
                (now + pd.Timedelta(days=90)).strftime("%Y-%m-%d"),
            ],
        ),
        yaxis=dict(
            showgrid=False,
            showticklabels=False,
            title="",
            range=[-0.5, 2.5],  # Fixed range for 3 rows
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        showlegend=True,
        hovermode="closest",
    )

    st.plotly_chart(fig, width="stretch")

