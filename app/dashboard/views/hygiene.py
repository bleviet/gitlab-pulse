"""Hygiene Page (Quality View) for Layer 3 Dashboard.

Quality scorecard and action table for data quality issues.
Refactored to use Widget Registry.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.utils import sort_hierarchy
from app.dashboard.widgets import charts, tables
from app.dashboard.widgets.quality_metrics import compute_quality_summary
from app.dashboard.widgets.tables.issue_detail_grid import issue_detail_grid
from app.dashboard.components import style_metric_cards
from app.dashboard.theme import get_alert_background_colors
from app.processor.rule_loader import DomainRule

# Error code severity mapping



def render_hygiene(
    valid_df: pd.DataFrame,
    quality_df: pd.DataFrame,
    rule: DomainRule | None = None,
) -> None:
    """Render the Hygiene (Quality) page.

    Args:
        valid_df: DataFrame with valid issues
        quality_df: DataFrame with quality hint issues
        rule: Active domain rule
    """
    st.caption("Quality view for metadata cleanup and validation")

    # Apply Bento Grid Style
    style_metric_cards()

    # Quality Scorecard (Collapsible) - using widget
    with st.expander("📊 Quality Score", expanded=True):
        charts.quality_gauge(valid_df, quality_df)
        summary = compute_quality_summary(valid_df, quality_df)
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Clean Issues", summary["clean_issues"])
        with col2:
            st.metric("Hinted Issues", summary["flagged_issues"])
        with col3:
            st.metric("Total Processed", summary["total_issues"])

    # Error Distribution and Action Table (Collapsible)
    if not quality_df.empty:
        selection = None
        with st.expander("📈 Error Distribution", expanded=True):
            selection = charts.error_distribution(quality_df)

        # Filter Action Table based on selection
        filtered_df = quality_df.copy()
        if selection and selection.get("selection", {}).get("points"):
            selected_points = selection["selection"]["points"]
            selected_errors: list[str] = []
            for point in selected_points:
                custom_data = point.get("customdata")
                if isinstance(custom_data, list) and custom_data:
                    selected_errors.append(str(custom_data[0]))
                elif point.get("y") is not None:
                    selected_errors.append(str(point["y"]))
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

