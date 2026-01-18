import os
import subprocess
import streamlit as st
import logging

logger = logging.getLogger(__name__)

def render_admin_view() -> None:
    """Render the Admin Interface for pipeline control."""
    st.header("⚡ Admin Operations")
    
    st.markdown("""
    Use this panel to manually trigger data updates or manage the dashboard cache.
    **Note:** Pipeline operations run on the server and may take a few moments.
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Data Pipeline")
        st.info("Trigger ingestion and processing steps manually.")
        
        if st.button("Run Collector (L1)", help="Fetch new data from GitLab API"):
            _run_pipeline_step(
                ["uv", "run", "python", "app/collector/orchestrator.py"],
                "Collector"
            )

        if st.button("Run Processor (L2)", help="Process raw data into analytics"):
            _run_pipeline_step(
                ["uv", "run", "python", "app/processor/main.py"],
                "Processor"
            )

    with col2:
        st.subheader("Dashboard Cache")
        st.info("Manage the ephemeral data cache (L3).")
        
        if st.button("Clear Cache", type="primary", help="Force reload of data from disk"):
            st.cache_data.clear()
            st.success("Cache cleared! Data will reload on next interaction.")

def _run_pipeline_step(command: list[str], name: str) -> None:
    """Execute a shell command and stream output."""
    status_container = st.empty()
    output_container = st.empty()
    
    status_container.status(f"Running {name}...", expanded=True)
    
    try:
        # Run command
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False
        )
        
        # Display logs
        with output_container.expander(f"{name} Logs", expanded=True):
            if result.stdout:
                st.code(result.stdout, language="text")
            if result.stderr:
                st.color_picker(f"{name} Error", "#FF0000", disabled=True, key=f"{name}_err_color") # Visual separator
                st.error(result.stderr)

        if result.returncode == 0:
            status_container.success(f"{name} completed successfully!")
            st.balloons()
        else:
            status_container.error(f"{name} failed with exit code {result.returncode}")
            
    except Exception as e:
        status_container.error(f"Failed to execute {name}: {str(e)}")
        logger.error(f"Admin execution error: {e}")
