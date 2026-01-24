"""Stale Issues List Table Widget."""

from typing import Any

import pandas as pd
import streamlit as st


def stale_issues_list(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> None:
    """Render table of stale issues.

    Args:
        df: DataFrame of issues
        config: Optional configuration with keys:
            - height: table height in pixels
    """
    config = config or {}
    height = config.get("height", 400)

    if "is_stale" not in df.columns:
        st.info("No staleness data available")
        return

    stale_df = df[df["is_stale"] == True].copy()

    if stale_df.empty:
        st.success("✅ No stale issues! All issues are actively maintained.")
        return

    # Select display columns
    display_cols = ["web_url", "title", "issue_type", "assignee", "age_days", "updated_at"]
    available_cols = [c for c in display_cols if c in stale_df.columns]

    display_df = stale_df[available_cols].copy()

    # Sort by age
    if "age_days" in display_df.columns:
        display_df = display_df.sort_values("age_days", ascending=False)

    # Format dates
    if "updated_at" in display_df.columns:
        display_df["updated_at"] = display_df["updated_at"].dt.strftime("%Y-%m-%d")

    # Rename for display
    display_df = display_df.rename(columns={
        "web_url": "IID",
        "title": "Title",
        "issue_type": "Type",
        "assignee": "Assignee",
        "age_days": "Age (Days)",
        "updated_at": "Last Update"
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
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Assignee": st.column_config.TextColumn("Assignee", width="medium"),
            "Age (Days)": st.column_config.NumberColumn("Age (Days)", width="small"),
            "Last Update": st.column_config.TextColumn("Last Update", width="medium"),
        },
    )
