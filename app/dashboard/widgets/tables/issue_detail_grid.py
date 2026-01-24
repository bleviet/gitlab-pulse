"""Issue Detail Grid Table Widget."""

from typing import Any

import pandas as pd
import streamlit as st

from app.dashboard.utils import sort_hierarchy


def issue_detail_grid(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> None:
    """Render unified issue detail grid with configurable columns.

    Args:
        df: DataFrame of issues
        config: Optional configuration with keys:
            - columns: list of column names to display
            - height: table height in pixels
            - title: optional header title
    """
    config = config or {}
    height = config.get("height", 600)
    title = config.get("title")

    if title:
        st.subheader(title)

    if df.empty:
        st.info("No issues to display")
        return

    # Default columns
    default_columns = ["web_url", "title", "issue_type", "stage", "assignee", "priority", "milestone"]
    columns = config.get("columns", default_columns)

    # Filter to available columns
    available_cols = [c for c in columns if c in df.columns]

    if not available_cols:
        st.warning("No displayable columns available")
        return

    display_df = df[available_cols].copy()

    # Sort by hierarchy if available
    if "parent_id" in df.columns and "iid" in df.columns:
        display_df = sort_hierarchy(display_df, parent_col="parent_id", id_col="iid", title_col="title")

    # Rename columns for display
    column_renames = {
        "web_url": "IID",
        "title": "Title",
        "issue_type": "Type",
        "stage": "Stage",
        "assignee": "Assignee",
        "priority": "Priority",
        "milestone": "Milestone",
        "age_days": "Age (Days)",
        "days_in_stage": "Days in Stage",
        "severity": "Severity",
    }
    display_df = display_df.rename(columns={k: v for k, v in column_renames.items() if k in display_df.columns})

    # Column configurations
    column_config = {
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
        "Age (Days)": st.column_config.NumberColumn("Age (Days)", width="small"),
        "Days in Stage": st.column_config.NumberColumn("Days in Stage", width="small"),
    }

    # Filter to relevant configs
    active_config = {k: v for k, v in column_config.items() if k in display_df.columns}

    st.dataframe(
        display_df,
        width="stretch",
        height=height,
        hide_index=True,
        column_config=active_config,
    )
