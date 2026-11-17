"""Milestone Timeline Chart Widget."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.theme import (
    FONT_CODE,
    get_active_theme_mode,
    get_palette,
    get_plotly_font_color,
    get_streamlit_theme_color,
    plotly_layout,
    with_alpha,
)


def milestone_timeline(
    issues_df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render milestone timeline as a scatter plot with markers.

    Args:
        issues_df: DataFrame with all issues (needed for completion stats)
        config: Optional configuration
            - key: widget key
            - height: chart height in pixels
            - style: ``"default"`` or ``"rail"``, a thin band with a centre
              rail, round markers alternating above and below it, and a
              "NOW" line
            - title: rail style only, a small label at the top left

    Returns:
        Selection state dictionary (if supported) or None
    """
    config = config or {}
    widget_key = config.get("key", "milestone_timeline")
    rail = config.get("style") == "rail"
    raw_height = config.get("height", 160)
    timeline_height = max(80, min(int(raw_height), 320))

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
    bg_color = get_streamlit_theme_color(
        "backgroundColor",
        "#050811" if get_active_theme_mode() == "dark" else "#f8f9fc",
    )
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
        has_highlight = bool(highlight_title)

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
        opacity = 0.25 if (has_highlight and not is_highlighted) else 1.0

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
            "opacity": opacity,
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
    # Rail style: in date order, milestones alternate above and below the
    # rail, so neighbours never overlap.
    chart_df["lane_y"] = [0.5 if index % 2 == 0 else -0.5 for index in range(len(chart_df))]

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
        if status_df.empty:
            continue
        # Split into normal (opacity=1) and dimmed (opacity<1) so Plotly can
        # apply per-group opacity (scatter opacity is trace-level, not per-point)
        for opacity_val, group_df in status_df.groupby("opacity", sort=False):
            is_dim = opacity_val < 1.0
            fig.add_trace(go.Scatter(
                x=group_df["date"],
                y=group_df["lane_y"] if rail else group_df["y_pos"],
                mode="markers+text",
                name=status,
                showlegend=not is_dim,  # only one legend entry per status
                opacity=float(opacity_val),
                marker=dict(
                    # Round dots with a ring in the page background colour,
                    # so they read as pins on the timeline (both styles).
                    size=group_df["size"] - 3,
                    color=color,
                    symbol="circle",
                    line=dict(
                        width=group_df["line_width"] + 2,
                        color=group_df["line_color"],
                    ),
                ),
                text=group_df["title"],
                textposition=(
                    ["top center" if y > 0 else "bottom center" for y in group_df["lane_y"]]
                    if rail
                    else "top center"
                ),
                textfont=dict(size=9 if rail else 10),
                hovertemplate=(
                    "<b>%{text}</b><br>"
                    "Due: %{customdata[0]}<br>"
                    "Issues: %{customdata[1]}<br>"
                    "Status: " + status +
                    "<extra></extra>"
                ),
                customdata=list(zip(group_df["date_str"], group_df["issues"], group_df["title"], strict=False)),
            ))

    today_str = now.strftime("%Y-%m-%d")
    date_range = [
        (now - pd.Timedelta(days=270)).strftime("%Y-%m-%d"),
        (now + pd.Timedelta(days=90)).strftime("%Y-%m-%d"),
    ]
    if rail:
        text_color = get_plotly_font_color()
        # Soft band with a centre rail, then the "now" line on top.
        fig.add_shape(
            type="rect",
            xref="paper",
            x0=0, x1=1,
            y0=-1.15, y1=1.15,
            fillcolor=with_alpha(text_color, 0.05),
            line=dict(width=0),
            layer="below",
        )
        fig.add_shape(
            type="line",
            xref="paper",
            x0=0, x1=1,
            y0=0, y1=0,
            line=dict(width=4, color=with_alpha(text_color, 0.12)),
            layer="below",
        )
        fig.add_shape(
            type="line",
            x0=today_str, x1=today_str,
            y0=-1.15, y1=1.15,
            line=dict(width=2, color=palette["now_marker"]),
        )
        # Below the band: milestone names sit above and inside it.
        fig.add_annotation(
            x=today_str,
            y=-1.15,
            yanchor="top",
            text="<b>NOW</b>",
            showarrow=False,
            font=dict(size=10, family=FONT_CODE, color=palette["now_marker"]),
        )
        title = config.get("title")
        if title:
            fig.add_annotation(
                x=0,
                xref="paper",
                xanchor="left",
                y=1.15,
                yanchor="bottom",
                text=f"<b>{title}</b>",
                showarrow=False,
                font=dict(size=9, color=with_alpha(text_color, 0.6)),
            )
        fig.update_layout(
            **plotly_layout(
                height=timeline_height,
                show_xgrid=True,
                show_ygrid=False,
                legend_pos="none",
                margin=dict(l=0, r=0, t=2, b=22),
            )
        )
        fig.update_xaxes(
            type="date",
            range=date_range,
            tickformat="%b %y",
            tickfont=dict(family=FONT_CODE, size=9),
            gridcolor=with_alpha(text_color, 0.08),
        )
        fig.update_yaxes(showticklabels=False, range=[-1.9, 1.9])
    else:
        _add_horizontal_today_and_axes(fig, today_str, date_range, timeline_height, palette)

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


def _add_horizontal_today_and_axes(
    fig: go.Figure,
    today_str: str,
    date_range: list[str],
    timeline_height: int,
    palette: Any,
) -> None:
    """Add the "Today" line, layout and axes of the horizontal timeline."""
    # Add vertical line for today using shape (avoids annotation arithmetic issues)
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
        font=dict(size=10, color=get_plotly_font_color()),
    )

    fig.update_layout(
        **plotly_layout(
            height=timeline_height,
            show_xgrid=True,
            show_ygrid=False,
            legend_pos="top",
            margin=dict(l=20, r=20, t=20, b=20),
        )
    )
    
    fig.update_xaxes(type="date", range=date_range)
    fig.update_yaxes(
        showticklabels=False,
        range=[-0.8, 2.2],  # Shifted down so top-row labels aren't clipped
    )
