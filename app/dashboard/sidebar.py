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

        # Context selector (for Data Explosion / sub-project filtering)
        contexts = ["All"]
        if not df.empty and "context" in df.columns:
            unique_contexts = df["context"].dropna().unique().tolist()
            contexts.extend(sorted(unique_contexts))

        selected_context = st.selectbox(
            "Context / Sub-Project",
            options=contexts,
            index=0,
            help="Filter by context (R&D project, Customer, etc.)",
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
        # Ensure stored date_range is within valid bounds
        stored_range = st.session_state.get("date_range", (min_date, max_date))
        if isinstance(stored_range, tuple) and len(stored_range) == 2:
            # Clamp to valid bounds
            start_val = max(stored_range[0], min_date)
            end_val = min(stored_range[1], max_date)
            if start_val > end_val:
                start_val = min_date
                end_val = max_date
            valid_range = (start_val, end_val)
        else:
            valid_range = (min_date, max_date)

        date_range = st.date_input(
            "Custom Range",
            value=valid_range,
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

        # Admin Access
        with st.expander("⚡ Admin Access"):
            import os
            
            if st.session_state.get("is_admin"):
                st.success("Authenticated")
                if st.button("Logout"):
                    st.session_state["is_admin"] = False
                    st.rerun()
            else:
                password = st.text_input("Password", type="password")
                if password:
                    # Default to 'admin' if env var not set
                    admin_pass = os.environ.get("ADMIN_PASSWORD", "admin")
                    if password == admin_pass:
                        st.session_state["is_admin"] = True
                        st.rerun()
                    else:
                        st.error("Invalid password")

    return {
        "team": selected_team,
        "context": selected_context,
        "start_date": pd.Timestamp(start_date, tz="UTC"),
        "end_date": pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1),
    }
