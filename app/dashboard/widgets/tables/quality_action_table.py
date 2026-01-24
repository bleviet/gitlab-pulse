"""Quality Action Table Widget."""

from typing import Any

import pandas as pd
import streamlit as st

# Error code severity mapping
ERROR_SEVERITY = {
    "MISSING_LABEL": "warning",
    "CONFLICTING_LABELS": "error",
    "STALE_WITHOUT_UPDATE": "warning",
    "ORPHAN_TASK": "error",
    "EXCEEDS_CYCLE_TIME": "info",
}


def quality_action_table(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> None:
    """Render action table for quality issues.

    Args:
        df: DataFrame of quality issues
        config: Optional configuration with keys:
            - height: table height in pixels
            - severity_map: dict mapping error codes to 'error', 'warning', 'info'
    """
    config = config or {}
    height = config.get("height", 400)
    widget_key = config.get("key", "quality_action_table")
    severity_map = config.get("severity_map", ERROR_SEVERITY)

    if df.empty:
        st.success("✅ No action items. All issues are valid.")
        return

    # Select display columns
    display_cols = ["web_url", "title", "error_code", "error_message", "assignee"]
    available_cols = [c for c in display_cols if c in df.columns]

    display_df = df[available_cols].copy()

    # Rename for display
    display_df = display_df.rename(columns={
        "web_url": "IID",
        "title": "Title",
        "error_code": "Error",
        "error_message": "Message",
        "assignee": "Assignee"
    })

    # Style the Error column
    def style_error_code(row: pd.Series) -> list[str]:
        code = row.get("Error", "")
        # Try to find code in map, default to info
        severity = severity_map.get(code, "info")
        bg_colors = {
            "error": "background-color: rgba(239,68,68,0.2)",
            "warning": "background-color: rgba(245,158,11,0.2)",
            "info": "background-color: rgba(100,116,139,0.1)",
        }
        style = bg_colors.get(severity, "")
        return [style if c == "Error" else "" for c in row.index]

    styled_df = display_df.style.apply(style_error_code, axis=1)

    st.dataframe(
        styled_df,
        width="stretch",
        height=height,
        hide_index=True,
        column_config={
            "IID": st.column_config.LinkColumn(
                "IID",
                display_text=r"/(?:issues|work_items)/(\d+)$",
                width="small",
            ),
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Error": st.column_config.TextColumn("Error", width="medium"),
            "Message": st.column_config.TextColumn("Message", width="large"),
            "Assignee": st.column_config.TextColumn("Assignee", width="medium"),
        },
        key=widget_key
    )
