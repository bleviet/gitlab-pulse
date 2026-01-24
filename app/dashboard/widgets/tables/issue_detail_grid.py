"""Issue Detail Grid Table Widget."""

from typing import Any, Union

import pandas as pd
from pandas.io.formats.style import Styler
import streamlit as st

from app.dashboard.utils import sort_hierarchy


def issue_detail_grid(
    data: Union[pd.DataFrame, Styler],
    config: dict[str, Any] | None = None
) -> Any:
    """Render unified issue detail grid with configurable columns.

    Args:
        data: DataFrame or Styler object
        config: Optional configuration with keys:
            - columns: list of column names to display (if DataFrame)
            - height: table height in pixels
            - title: optional header title
            - minimize_columns: bool (default True) to filter columns
            - column_config: dict of column configurations to merge/override
            - column_order: list of column names for ordering
            - selection_mode: "single-row", "multi-row" (default "multi-row")
            - key: widget key

    Returns:
        Selection object from st.dataframe
    """
    config = config or {}
    height = config.get("height", 600)
    title = config.get("title")
    widget_key = config.get("key", "issue_detail_grid")
    selection_mode = config.get("selection_mode", "multi-row")

    if title:
        st.subheader(title)

    # Check if data is Styler
    is_styler = isinstance(data, Styler)
    
    if is_styler:
        # If Styler, we assume pre-processing (filtering/sorting) is done by caller
        display_data = data
        df = data.data # Access underlying dataframe for column checks if needed
    else:
        df = data
        if df.empty:
            st.info("No issues to display")
            return None

        # Filters expander (Skip if explicitly disabled or if using Styler which implies external control)
        # We only show filters for raw DataFrames
        if config.get("enable_filters", True):
            with st.expander("🔍 Filters", expanded=False):
                filter_cols = st.columns(3)

                # Stage filter
                if "stage" in df.columns:
                    with filter_cols[0]:
                        all_stages = sorted(df["stage"].dropna().unique().tolist())
                        
                        # Reset filter logic (simplified for shared widget)
                        filter_key = f"{widget_key}_stage_filter"
                        selected_stages = st.multiselect(
                            "Stage",
                            options=all_stages,
                            default=all_stages,
                            key=filter_key
                        )
                        if selected_stages:
                            df = df[df["stage"].isin(selected_stages)]

                # Assignee filter
                if "assignee" in df.columns:
                    with filter_cols[1]:
                        all_assignees = ["All"] + sorted(df["assignee"].dropna().unique().tolist())
                        key_assignee = f"{widget_key}_assignee_filter"
                        selected_assignee = st.selectbox(
                            "Assignee",
                            options=all_assignees,
                            key=key_assignee
                        )
                        if selected_assignee != "All":
                            df = df[df["assignee"] == selected_assignee]

                # Type filter
                if "issue_type" in df.columns:
                    with filter_cols[2]:
                        all_types = sorted(df["issue_type"].dropna().unique().tolist())
                        filter_key_type = f"{widget_key}_type_filter"
                        selected_types = st.multiselect(
                            "Type",
                            options=all_types,
                            default=all_types,
                            key=filter_key_type
                        )
                        if selected_types:
                            df = df[df["issue_type"].isin(selected_types)]

        # Column handling
        # Column handling
        # User request: "The table should have the possiblity display all the issue details..."
        # We generally avoid hard-dropping columns.
    display_df = df.copy()

    # Column Renames (Defined here for scope availability)
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
        "weight": "Weight",
        "context": "Context",
        "error_code": "Error",
        "error_message": "Message",
        "updated_at": "Last Update"
    }

    if is_styler:
        # If Styler, underlying data is in data.data
        # We cannot easily rename columns in a Styler object without reconstructing it or using specific pandas calls
        # which might break existing styles. 
        # However, users passing a Styler usually have already set up the display dataframe.
        # But if we want to apply our standard column configs (which use renmaed global keys like 'IID'), 
        # the styler data must match.
        # Ideally, caller should rename BEFORE styling.
        # For now, we assume Styler input has valid columns or we mapped them earlier in the View.
        # IMPORTANT: 'column_renames' is mainly for raw DF handling. 
        display_data = data
    else:
        # Sort by hierarchy if available
        if "parent_id" in df.columns and "iid" in df.columns:
            display_df = sort_hierarchy(display_df, parent_col="parent_id", id_col="iid", title_col="title")

        display_df = display_df.rename(columns={k: v for k, v in column_renames.items() if k in display_df.columns})
        display_data = display_df

    # Default configured columns (mapped to new names)
    default_columns_raw = ["web_url", "title", "issue_type", "stage", "assignee", "priority", "milestone"]
    
    # Map raw config columns to display names
    def map_col(c):
        return column_renames.get(c, c)

    defaults_mapped = [map_col(c) for c in default_columns_raw]
    
    # Get user config columns and map them
    user_cols_raw = config.get("columns", default_columns_raw)
    column_order = [map_col(c) for c in user_cols_raw if c in df.columns]

    # If column_order is not passed explicitly in config['column_order'], use the mapped 'columns' list
    final_column_order = config.get("column_order", column_order)

    # Base Column Configuration


    # Base Column Configuration
    base_config = {
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
        "Weight": st.column_config.NumberColumn("Weight", width="small"),
        "Context": st.column_config.TextColumn("Context", width="small"),
        "Error": st.column_config.TextColumn("Error", width="medium"),
        "Message": st.column_config.TextColumn("Message", width="large"),
        "Last Update": st.column_config.TextColumn("Last Update", width="medium"),
    }

    # Merge with user config (user config takes precedence)
    user_col_config = config.get("column_config", {})
    final_col_config = {**base_config, **user_col_config}

    # Render
    return st.dataframe(
        display_data,
        width="stretch",
        height=height,
        hide_index=True,
        column_config=final_col_config,
        column_order=final_column_order,
        on_select="rerun",
        selection_mode=selection_mode,
        key=widget_key
    )
