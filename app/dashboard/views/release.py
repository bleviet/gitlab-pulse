"""Release management dashboard view.

Visualizes release readiness, burn-up charts, and scope management.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.shared.schemas import AnalyticsIssue


def render_release_view(df: pd.DataFrame) -> None:
    """Render the release management dashboard.
    
    Args:
        df: DataFrame containing all issues
    """
    st.header("Release Management")
    
    # 1. Milestone Selection
    if "milestone_id" not in df.columns or df["milestone_id"].isnull().all():
        st.warning("No milestone data available.")
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
        remaining = (due_date - pd.Timestamp.now()).days
        days_remaining = f"{remaining} days"
        
        if remaining < 0 and pct_complete < 100:
            status_color = "inverse" # Late
        elif remaining < 7 and pct_complete < 80:
            status_color = "normal" # At Risk (using normal as warning-ish?)
            
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Progress", f"{pct_complete:.1f}%", f"{closed_issues}/{total_issues} Issues")
    col2.metric("Days Remaining", days_remaining)
    col3.metric("Scope", total_issues, help="Total issues in milestone")
    
    # 3. Burn-up Chart
    _render_burnup_chart(ms_data, ms_meta)
    
    # 4. Scope Table
    st.subheader("Release Scope")
    
    # Format for display
    display_df = ms_data.copy()
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
        scope_counts = pd.Series(dtype=int)
    
    # Closed (Completed) -> Convert to Naive UTC
    completed_df = df[df["state"] == "closed"].copy()
    if not completed_df.empty:
        completed_df["closed_date"] = pd.to_datetime(completed_df["closed_at"]).apply(to_naive_utc).dt.normalize()
        completed_counts = completed_df.groupby("closed_date").size().sort_index().cumsum()
    else:
        completed_counts = pd.Series(dtype=int)
    
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
        legend=dict(orientation="h", y=1.1)
    )
    
    st.plotly_chart(fig)
