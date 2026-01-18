"""Sidebar component for Layer 3 Dashboard.

Provides domain selector, time range picker, and sync status.
"""

from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st


def render_sidebar(df: pd.DataFrame) -> dict[str, Any]:
    """Render the global sidebar with filters.

    Args:
        df: DataFrame to extract filter options from

    Returns:
        Dict with selected filter values
    """
    with st.sidebar:
        # Header
        st.title("🔍 GitLabInsight")
        st.caption("Analytics Dashboard")

        st.divider()

        # Domain/Team selector
        teams = ["All"]
        if not df.empty and "team" in df.columns:
            unique_teams = df["team"].dropna().unique().tolist()
            teams.extend(sorted(unique_teams))

        selected_team = st.selectbox(
            "Domain / Team",
            options=teams,
            index=0,
            help="Filter issues by team or domain",
        )

        st.divider()

        # Time range picker
        st.subheader("📅 Time Range")

        # Calculate date bounds from data
        if not df.empty and "created_at" in df.columns:
            min_date = df["created_at"].min().date()
            max_date = df["created_at"].max().date()
        else:
            max_date = datetime.now().date()
            min_date = max_date - timedelta(days=365)

        # Quick range buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("30 Days", width="stretch"):
                st.session_state.date_range = (
                    max_date - timedelta(days=30),
                    max_date,
                )
        with col2:
            if st.button("90 Days", width="stretch"):
                st.session_state.date_range = (
                    max_date - timedelta(days=90),
                    max_date,
                )

        col3, col4 = st.columns(2)
        with col3:
            if st.button("1 Year", width="stretch"):
                st.session_state.date_range = (
                    max_date - timedelta(days=365),
                    max_date,
                )
        with col4:
            if st.button("All Time", width="stretch"):
                st.session_state.date_range = (min_date, max_date)

        # Date range slider
        date_range = st.date_input(
            "Custom Range",
            value=st.session_state.get("date_range", (min_date, max_date)),
            min_value=min_date,
            max_value=max_date,
            help="Select start and end dates",
        )

        # Handle single date selection
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        else:
            start_date = end_date = date_range

        st.divider()

        # Sync status footer
        from app.dashboard.data_loader import get_sync_status

        sync_status = get_sync_status()
        st.caption(f"**Status:** {sync_status['status']}")
        st.caption(f"**Last Sync:** {sync_status['last_sync']}")

        # Version
        st.divider()
        st.caption("v0.1.0")

    return {
        "team": selected_team,
        "start_date": pd.Timestamp(start_date, tz="UTC"),
        "end_date": pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1),
    }
