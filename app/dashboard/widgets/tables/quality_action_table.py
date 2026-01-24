"""Quality Action Table Widget."""

from typing import Any

import pandas as pd
import streamlit as st


def quality_action_table(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> None:
    """Render action table for quality issues.

    Args:
        df: DataFrame of quality issues
        config: Optional configuration with keys:
            - height: table height in pixels
    """
    config = config or {}
    height = config.get("height", 400)

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

    st.dataframe(
        display_df,
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
    )
