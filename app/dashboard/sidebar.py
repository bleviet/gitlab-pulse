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

        # Milestone selector
        milestones = ["All"]
        if not df.empty and "milestone" in df.columns:
            # Drop None/NaN and sort
            unique_milestones = df["milestone"].dropna().unique().tolist()
            milestones.extend(sorted(unique_milestones))

        selected_milestone = st.selectbox(
            "Milestone",
            options=milestones,
            index=0,
            help="Filter specific milestone",
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

        # Handle single date selection (st.date_input can return single date or tuple)
        if isinstance(date_range, tuple):
            if len(date_range) == 2:
                start_date, end_date = date_range
            elif len(date_range) == 1:
                start_date = end_date = date_range[0]
            else:
                start_date = end_date = min_date
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

        # --- Ollama Server Settings ---
        with st.expander("🤖 AI Settings"):
            import json
            from pathlib import Path

            # State file path
            state_dir = Path("data/state")
            state_dir.mkdir(parents=True, exist_ok=True)
            ollama_state_file = state_dir / "ollama_servers.json"

            # Load saved servers
            def load_saved_servers() -> list[str]:
                if ollama_state_file.exists():
                    try:
                        with open(ollama_state_file, "r") as f:
                            data = json.load(f)
                            return data.get("servers", ["http://localhost:11434"])
                    except Exception:
                        pass
                return ["http://localhost:11434"]

            def save_servers(servers: list[str]):
                with open(ollama_state_file, "w") as f:
                    json.dump({"servers": servers}, f)

            saved_servers = load_saved_servers()

            # Initialize session state (Smart Auto-discovery)
            if "ollama_endpoint" not in st.session_state:
                # Default to None, then probe
                active_endpoint = None

                # Probing known servers to find the first working one
                # This solves the issue of defaulting to an offline server when a working one exists
                import requests
                for server in saved_servers:
                    try:
                        # Short timeout for probing
                        resp = requests.get(f"{server.rstrip('/')}/", timeout=0.5)
                        if resp.status_code == 200:
                            active_endpoint = server
                            break
                    except Exception:
                        continue

                # Fallback to first if none found (or if list empty, default)
                if not active_endpoint:
                     active_endpoint = saved_servers[0] if saved_servers else "http://localhost:11434"

                st.session_state.ollama_endpoint = active_endpoint

            # Server selection dropdown
            server_options = saved_servers.copy()
            current_idx = 0
            if st.session_state.ollama_endpoint in server_options:
                current_idx = server_options.index(st.session_state.ollama_endpoint)

            selected_server = st.selectbox(
                "Ollama Server",
                options=server_options,
                index=current_idx,
                key="ollama_server_select"
            )

            if selected_server != st.session_state.ollama_endpoint:
                st.session_state.ollama_endpoint = selected_server
                st.rerun()

            # Add new server
            new_server = st.text_input(
                "Add Server URL",
                placeholder="http://192.168.1.100:11434",
                key="new_ollama_server"
            )

            col_add, col_del = st.columns(2)

            with col_add:
                if st.button("➕ Add", disabled=not new_server):
                    if new_server and new_server not in saved_servers:
                        # Validate URL format
                        if not new_server.startswith(("http://", "https://")):
                            st.error("URL must start with http:// or https://")
                        else:
                            # Test connection
                            import requests
                            try:
                                resp = requests.get(f"{new_server.rstrip('/')}/", timeout=2)
                                if resp.status_code == 200:
                                    saved_servers.append(new_server)
                                    save_servers(saved_servers)
                                    st.session_state.ollama_endpoint = new_server
                                    st.success("✅ Server added!")
                                    st.rerun()
                                else:
                                    st.error(f"Server responded with {resp.status_code}")
                            except requests.RequestException as e:
                                st.error(f"Connection failed: {e}")

            with col_del:
                if st.button("🗑️ Delete", disabled=(len(saved_servers) <= 1 or selected_server == "http://localhost:11434")):
                    if selected_server in saved_servers:
                        saved_servers.remove(selected_server)
                        save_servers(saved_servers)
                        st.session_state.ollama_endpoint = saved_servers[0]
                        st.rerun()

            # Show connection status
            st.caption(f"**Active:** {st.session_state.ollama_endpoint}")

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
        "milestone": selected_milestone,
        "start_date": pd.Timestamp(start_date, tz="UTC"),
        "end_date": pd.Timestamp(end_date, tz="UTC") + pd.Timedelta(days=1) - pd.Timedelta(seconds=1),
    }
