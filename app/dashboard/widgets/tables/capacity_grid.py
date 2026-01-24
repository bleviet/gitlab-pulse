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
    widget_key = config.get("key", "capacity_grid")

    # Interactive Filters
    with st.expander("🔍 Filters", expanded=False):
        title_search = st.text_input(
            "Search Title",
            placeholder="Type to search issue titles...",
            key=f"{widget_key}_search"
        )

        filter_cols = st.columns(3)

        with filter_cols[0]:
            if "assignee" in df.columns:
                available_assignees = sorted(df["assignee"].dropna().unique().tolist())
                selected_assignees = st.multiselect(
                    "Assignee",
                    options=available_assignees,
                    key=f"{widget_key}_assignee"
                )
            else:
                selected_assignees = []

        with filter_cols[1]:
            priorities = []
            if "priority" in df.columns:
                priorities = sorted(df["priority"].dropna().unique().tolist())
                p_label = "Priority"
            elif "severity" in df.columns:
                priorities = sorted(df["severity"].dropna().unique().tolist())
                p_label = "Priority (Severity)"
            
            selected_priorities = []
            if priorities:
                selected_priorities = st.multiselect(
                    p_label if priorities else "Priority",
                    options=priorities,
                    key=f"{widget_key}_priority"
                )

        with filter_cols[2]:
            if "milestone" in df.columns:
                available_milestones = sorted(df["milestone"].dropna().unique().tolist())
                selected_milestones = st.multiselect(
                    "Milestone",
                    options=available_milestones,
                    key=f"{widget_key}_milestone"
                )
            else:
                selected_milestones = []

    # Apply Filters
    work_df = df.copy()

    if title_search:
        work_df = work_df[work_df["title"].str.contains(title_search, case=False, na=False)]
    if selected_assignees:
        work_df = work_df[work_df["assignee"].isin(selected_assignees)]
    if selected_priorities:
        p_col = "priority" if "priority" in work_df.columns else "severity"
        work_df = work_df[work_df[p_col].isin(selected_priorities)]
    if selected_milestones:
        work_df = work_df[work_df["milestone"].isin(selected_milestones)]

    if work_df.empty:
        st.info("No issues match the current filters")
        return

    # Sort if possible
    if "assignee" in work_df.columns and "days_in_stage" in work_df.columns:
        work_df = work_df.sort_values(["assignee", "days_in_stage"], ascending=[True, False])

    # Select display columns
    display_cols = ["web_url", "assignee", "title", "stage", "priority", "milestone", "days_in_stage", "context", "weight"]
    available_cols = [c for c in display_cols if c in work_df.columns]
    
    display_df = work_df[available_cols].copy()

    # Column Renames for nice display
    renames = {
        "web_url": "IID",
        "title": "Title", 
        "stage": "Stage",
        "assignee": "Assignee",
        "priority": "Priority",
        "milestone": "Milestone",
        "days_in_stage": "Age",
        "context": "Context",
        "weight": "Weight"
    }
    display_df = display_df.rename(columns={k: v for k, v in renames.items() if k in display_df.columns})

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
            "Assignee": st.column_config.TextColumn("Assignee", width="medium"),
            "Age": st.column_config.NumberColumn("Age", format="%d days"),
            "Context": st.column_config.TextColumn("Context", width="small"),
        },
    )
