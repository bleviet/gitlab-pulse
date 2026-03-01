"""Daily Report Page for Layer 3 Dashboard.

Operational snapshot of issue activity for a single 24-hour window (midnight to midnight UTC).
Supports backward and forward navigation across days.
"""

import pandas as pd
import streamlit as st

from app.dashboard.components import style_metric_cards
from app.dashboard.widgets import charts, kpis
from app.dashboard.widgets.tables.issue_detail_grid import issue_detail_grid


def render_daily_report(
    df: pd.DataFrame,
) -> None:
    """Render the Daily Report page.

    Shows issue activity for a single 24-hour window (midnight to midnight UTC).
    Defaults to yesterday. Use the navigation buttons to move back or forward
    one day at a time.

    Args:
        df: Filtered DataFrame with valid issues
    """
    # --- Day navigation ---
    if "daily_day_offset" not in st.session_state:
        st.session_state.daily_day_offset = 0

    today_midnight = pd.Timestamp.now(tz="UTC").normalize()
    offset = st.session_state.daily_day_offset
    if offset >= 0:
        # Most-forward position: yesterday midnight → now
        window_start = today_midnight - pd.Timedelta(days=1)
        window_end = pd.Timestamp.now(tz="UTC")
    else:
        # Historical: strict midnight-to-midnight window
        window_end = today_midnight + pd.Timedelta(days=offset)
        window_start = window_end - pd.Timedelta(days=1)

    start_display = window_start.strftime("%Y-%m-%d 00:00 UTC")
    end_display = window_end.strftime("%Y-%m-%d %H:%M UTC")
    st.caption(f"Showing activity: **{start_display}** → **{end_display}**")

    col_back, col_fwd = st.columns([1, 1])
    with col_back:
        if st.button("◀ Back", use_container_width=True):
            st.session_state.daily_day_offset -= 1
            st.rerun()
    with col_fwd:
        if st.button(
            "Forward ▶",
            use_container_width=True,
            disabled=st.session_state.daily_day_offset >= 0,
        ):
            st.session_state.daily_day_offset += 1
            st.rerun()

    if df.empty:
        st.warning("No data available. Run the collector and processor first.")
        return

    # Apply Bento Grid Style
    style_metric_cards()

    # KPI Row
    kpis.daily_summary_kpi(df, {"cutoff": window_start, "cutoff_end": window_end})

    # New Issues Table
    new_df = pd.DataFrame()
    if "created_at" in df.columns:
        new_df = df[(df["created_at"] >= window_start) & (df["created_at"] < window_end)].copy()

    with st.expander(f"🆕 New Issues ({len(new_df)})", expanded=True):
        if new_df.empty:
            st.info("No new issues in this period.")
        else:
            issue_detail_grid(
                new_df,
                config={
                    "key": "daily_new_issues_grid",
                    "columns": ["web_url", "title", "issue_type", "assignee", "severity", "milestone"],
                },
            )

    # Closed Issues Table
    closed_df = pd.DataFrame()
    if "closed_at" in df.columns:
        closed_df = df[(df["closed_at"] >= window_start) & (df["closed_at"] < window_end)].copy()

    with st.expander(f"✅ Closed Issues ({len(closed_df)})", expanded=True):
        if closed_df.empty:
            st.info("No issues closed in this period.")
        else:
            issue_detail_grid(
                closed_df,
                config={
                    "key": "daily_closed_issues_grid",
                    "columns": ["web_url", "title", "issue_type", "assignee", "severity", "milestone"],
                },
            )
