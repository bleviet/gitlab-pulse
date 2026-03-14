"""Hygiene Page (Quality View) for Layer 3 Dashboard.

Quality scorecard and action table for data quality issues.
Refactored to use Widget Registry.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.utils import sort_hierarchy
from app.dashboard.widgets import charts, tables
from app.dashboard.widgets.tables.issue_detail_grid import issue_detail_grid
from app.dashboard.components import style_metric_cards
from app.dashboard.theme import get_alert_background_colors

# Error code severity mapping



def render_hygiene(valid_df: pd.DataFrame, quality_df: pd.DataFrame) -> None:
    """Render the Hygiene (Quality) page.

    Args:
        valid_df: DataFrame with valid issues
        quality_df: DataFrame with quality (failed) issues
    """
    st.caption("Quality view for metadata cleanup and validation")

    # Apply Bento Grid Style
    style_metric_cards()

    # Quality Scorecard (Collapsible) - using widget
    with st.expander("📊 Quality Score", expanded=True):
        charts.quality_gauge(valid_df, quality_df)
        # Summary metrics
        total_valid = len(valid_df)
        total_quality = len(quality_df)
        total = total_valid + total_quality
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Valid Issues", total_valid)
        with col2:
            st.metric("Failed Issues", total_quality)
        with col3:
            st.metric("Total Processed", total)

    # Error Distribution and Action Table (Collapsible)
    if not quality_df.empty:
        selection = None
        with st.expander("📈 Error Distribution", expanded=True):
            selection = charts.error_distribution(quality_df)

        # Filter Action Table based on selection
        filtered_df = quality_df.copy()
        if selection and selection.get("selection", {}).get("points"):
            selected_points = selection["selection"]["points"]
            # Error code is on the Y axis
            selected_errors = [p["y"] for p in selected_points]
            if selected_errors:
                filtered_df = filtered_df[filtered_df["error_code"].isin(selected_errors)]

        with st.expander("⚡ Action Items", expanded=True):
            # Sort hierarchy for better context
            display_df = filtered_df.copy()
            if "parent_id" in display_df.columns:
                 display_df = sort_hierarchy(display_df, parent_col="parent_id", id_col="iid", title_col="title")
            
            # Rename columns before styling (because issue_detail_grid doesn't rename Styler data)
            renames = {
                "web_url": "IID",
                "title": "Title",
                "error_code": "Error",
                "error_message": "Message",
                "assignee": "Assignee"
            }
            display_df = display_df.rename(columns={k: v for k, v in renames.items() if k in display_df.columns})

            # Style the Error column (logic moved from widget)
            ERROR_SEVERITY = {
                "MISSING_LABEL": "warning",
                "CONFLICTING_LABELS": "error",
                "STALE_WITHOUT_UPDATE": "warning",
                "ORPHAN_TASK": "error",
                "EXCEEDS_CYCLE_TIME": "info",
            }
            
            def style_error_code(row: pd.Series) -> list[str]:
                code = row.get("Error", "")
                severity = ERROR_SEVERITY.get(code, "info")
                bg_colors = get_alert_background_colors()
                style = bg_colors.get(severity, "")
                return [style if c == "Error" else "" for c in row.index]

            styler = display_df.style.apply(style_error_code, axis=1)

            tables.issue_detail_grid(
                styler, 
                config={
                    "key": "hygiene_action_table",
                    # Pass the NEW names because Styler data already has them
                    "columns": ["IID", "Title", "Error", "Message", "Assignee"],
                    "column_config": {
                         "Error": st.column_config.TextColumn("Error", width="medium"),
                         "Message": st.column_config.TextColumn("Message", width="large")
                    }
                }
            )
    else:
        st.success("✅ Perfect data quality! All issues passed validation.")



