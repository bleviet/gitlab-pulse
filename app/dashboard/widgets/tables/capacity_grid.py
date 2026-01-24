"""Capacity Grid Table Widget."""

from typing import Any

import pandas as pd
import streamlit as st


def capacity_grid(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> None:
    """Render filterable grid of active work for capacity view.

    Args:
        df: DataFrame of issues
        config: Optional configuration with keys:
            - assignee_filter: filter by specific assignee
            - stage_filter: filter by specific stage
            - height: table height in pixels
    """
    config = config or {}
    height = config.get("height", 500)
    assignee_filter = config.get("assignee_filter")
    stage_filter = config.get("stage_filter")

    work_df = df.copy()

    # Apply filters
    if assignee_filter:
        work_df = work_df[work_df["assignee"] == assignee_filter]
    if stage_filter:
        work_df = work_df[work_df["stage"] == stage_filter]

    if work_df.empty:
        st.info("No issues match the current filters")
        return

    # Select display columns
    display_cols = ["web_url", "title", "issue_type", "stage", "assignee", "priority", "milestone", "days_in_stage"]
    available_cols = [c for c in display_cols if c in work_df.columns]

    display_df = work_df[available_cols].copy()

    # Rename for display
    display_df = display_df.rename(columns={
        "web_url": "IID",
        "title": "Title",
        "issue_type": "Type",
        "stage": "Stage",
        "assignee": "Assignee",
        "priority": "Priority",
        "milestone": "Milestone",
        "days_in_stage": "Days in Stage"
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
            "Stage": st.column_config.TextColumn("Stage", width="small"),
            "Assignee": st.column_config.TextColumn("Assignee", width="medium"),
            "Priority": st.column_config.TextColumn("Priority", width="small"),
            "Milestone": st.column_config.TextColumn("Milestone", width="medium"),
            "Days in Stage": st.column_config.NumberColumn("Days in Stage", width="small"),
        },
    )
