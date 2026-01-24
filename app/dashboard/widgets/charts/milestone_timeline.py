"""Milestone Timeline Chart Widget."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def milestone_timeline(
    milestones_df: pd.DataFrame,
    issues_df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render milestone timeline as a scatter plot with markers.

    Args:
        milestones_df: DataFrame with milestone details (id, title, due_date, start_date, state)
        issues_df: DataFrame with all issues (needed for completion stats)
        config: Optional configuration
            - key: widget key

    Returns:
        Selection state dictionary (if supported) or None
    """
    config = config or {}
    widget_key = config.get("key", "milestone_timeline")

    if milestones_df.empty:
        st.info("No milestones to display.")
        return None

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
        all_issues_closed = stats["total"] > 0 and stats["closed"] == stats["total"]

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
                # Check for "At Risk"? For now strictly On Track or Overdue
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
        return None

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
                # Add title to customdata[2] for selection
                customdata=list(zip(status_df["date_str"], status_df["issues"], status_df["title"])),
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
    )

    selection = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        selection_mode=["points"],
        key=widget_key
    )

    return selection
