"""Milestone Timeline Chart Widget."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.theme import get_palette, get_streamlit_theme_color, plotly_layout, with_alpha


def milestone_timeline(
    issues_df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render milestone timeline as a scatter plot with markers.

    Args:
        issues_df: DataFrame with all issues (needed for completion stats)
        config: Optional configuration
            - key: widget key

    Returns:
        Selection state dictionary (if supported) or None
    """
    config = config or {}
    widget_key = config.get("key", "milestone_timeline")

    display_df = None

    # Extract from Issues (e.g. for Subprojects/Groups)
    if (display_df is None or display_df.empty) and not issues_df.empty and "milestone_id" in issues_df.columns:
        # Group by milestone title/id to reconstruct milestone metadata
        # We need id, title, due_date, start_date, state

        # Ensure we have the necessary columns
        available_cols = issues_df.columns
        agg_dict = {
            "milestone_id": "first",
            "state": lambda x: "closed" if (x == "closed").all() else "active"
        }

        if "milestone_due_date" in available_cols:
            agg_dict["milestone_due_date"] = "first"
        if "milestone_start_date" in available_cols:
            agg_dict["milestone_start_date"] = "first"

        # Group by milestone title (as it's usually reliable)
        if "milestone" in available_cols:
            ms_agg = issues_df[issues_df["milestone"].notna()].groupby("milestone").agg(agg_dict).reset_index()

            # Rename to match expected schema
            rename_map = {
                "milestone": "title",
                "milestone_id": "id",
            }
            if "milestone_due_date" in available_cols:
                rename_map["milestone_due_date"] = "due_date"
            if "milestone_start_date" in available_cols:
                rename_map["milestone_start_date"] = "start_date"

            ms_agg = ms_agg.rename(columns=rename_map)

            # Ensure required columns exist even if missing from source
            if "due_date" not in ms_agg.columns:
                ms_agg["due_date"] = pd.NaT
            if "start_date" not in ms_agg.columns:
                ms_agg["start_date"] = pd.NaT

            display_df = ms_agg

    if display_df is None or display_df.empty:
        st.info("No milestones to display.")
        return None

    now = pd.Timestamp.now(tz="UTC")

    # Calculate issue completion per milestone
    milestone_issue_stats = {}
    if not issues_df.empty and "milestone_id" in issues_df.columns:
        for ms_id in display_df["id"].unique():
            ms_issues = issues_df[issues_df["milestone_id"] == ms_id]
            total = len(ms_issues)
            closed = len(ms_issues[ms_issues["state"] == "closed"])
            milestone_issue_stats[ms_id] = {"total": total, "closed": closed}

    # Prepare scatter data
    # Resolve background color once for marker outline "floating" effect
    bg_color = get_streamlit_theme_color("backgroundColor", "#050811")
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

        # Highlight logic from config (e.g. linked to sidebar)
        highlight_title = config.get("highlight_milestone")
        is_highlighted = title == highlight_title

        palette = get_palette()
        if state == "closed":
            if all_issues_closed:
                color = palette["ms_complete"]
                status = "Complete"
            else:
                color = palette["ms_incomplete"]
                status = "Incomplete"
        else:
            if pd.notna(due_date) and due_date < now:
                color = palette["ms_overdue"]
                status = "Overdue"
            else:
                color = palette["ms_on_track"]
                status = "On Track"

        # Apply highlight visual overrides
        size = 16
        line_width = 1
        line_color = bg_color  # matches background for a "floating" marker effect

        if is_highlighted:
            size = 22
            line_width = 3
            line_color = palette["ms_highlight"]

        # Format date for display
        date_str = marker_date.strftime("%Y-%m-%d") if pd.notna(marker_date) else "No date"

        scatter_data.append({
            "date": marker_date,
            "date_str": date_str,
            "title": title,
            "status": status,
            "color": color,
            "issues": f"{stats['closed']}/{stats['total']}",
            "size": size,
            "line_width": line_width,
            "line_color": line_color,
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
    palette = get_palette()
    status_colors = {
        "Complete": palette["ms_complete"],
        "Incomplete": palette["ms_incomplete"],
        "On Track": palette["ms_on_track"],
        "Overdue": palette["ms_overdue"],
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
                    size=status_df["size"],
                    color=color,
                    symbol="diamond",
                    line=dict(
                        width=status_df["line_width"],
                        color=status_df["line_color"]
                    ),
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
                customdata=list(zip(status_df["date_str"], status_df["issues"], status_df["title"], strict=False)),
            ))

    # Add vertical line for today using shape (avoids annotation arithmetic issues)
    today_str = now.strftime("%Y-%m-%d")
    fig.add_shape(
        type="line",
        x0=today_str, x1=today_str,
        y0=0, y1=1,
        yref="paper",
        line=dict(width=2, dash="dash", color=with_alpha(palette["neutral"], 0.8)),
    )
    fig.add_annotation(
        x=today_str,
        y=1.05,
        yref="paper",
        text="Today",
        showarrow=False,
        font=dict(size=10),
    )

    fig.update_layout(
        **plotly_layout(
            height=200,
            show_xgrid=True,
            show_ygrid=False,
            legend_pos="top",
            margin=dict(l=20, r=20, t=40, b=20),
        )
    )
    
    fig.update_xaxes(
        type="date",
        range=[
            (now - pd.Timedelta(days=270)).strftime("%Y-%m-%d"),
            (now + pd.Timedelta(days=90)).strftime("%Y-%m-%d"),
        ],
    )
    fig.update_yaxes(
        showticklabels=False,
        range=[-0.5, 2.5],  # Fixed range for 3 rows
    )

    selection = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        selection_mode=["points"],
        key=widget_key
    )

    return selection
