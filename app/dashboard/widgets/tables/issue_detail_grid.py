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
    title = config.get("title")
    widget_key = config.get("key", "issue_detail_grid")
    selection_mode = config.get("selection_mode", "multi-row")
    default_page_size = config.get("page_size", 25)

    if title:
        st.subheader(title)

    # Check if data is Styler
    is_styler = isinstance(data, Styler)

    if is_styler:
        # If Styler, we assume pre-processing (filtering/sorting) is done by caller
        display_data = data
        df = data.data  # Access underlying dataframe for column checks if needed
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
        # We cannot easily rename columns in a Styler object without reconstructing it
        # or using specific pandas calls which might break existing styles.
        # However, users passing a Styler usually have already set up the display dataframe.
        # But if we want to apply our standard column configs (which use renamed global
        # keys like 'IID'), the styler data must match.
        # Ideally, caller should rename BEFORE styling.
        # For now, we assume Styler input has valid columns or we mapped them earlier
        # in the View.
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
    def map_col(c: str) -> str:
        return column_renames.get(c, c)

    defaults_mapped = [map_col(c) for c in default_columns_raw]

    # Get user config columns and map them
    user_cols_raw = config.get("columns", default_columns_raw)
    column_order = [map_col(c) for c in user_cols_raw if c in df.columns]

    # If column_order is not passed explicitly in config['column_order'], use the mapped 'columns' list
    final_column_order = config.get("column_order", column_order)

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

    # --- Pagination ---
    total_rows = len(display_data.data) if is_styler else len(display_data)
    page_size_options = [25, 50, 100]
    show_all_label = f"All ({total_rows})"

    page_size_choice = st.selectbox(
        "Rows per page",
        options=page_size_options + [show_all_label],
        index=page_size_options.index(default_page_size) if default_page_size in page_size_options else 1,
        key=f"{widget_key}_page_size",
        help="Number of rows to display",
    )

    show_all = isinstance(page_size_choice, str) and page_size_choice.startswith("All")

    if show_all:
        page_display = display_data
        computed_height = config.get("height", 35 * total_rows + 45)
    else:
        page_size = int(page_size_choice)
        total_pages = max(1, -(-total_rows // page_size))  # ceil division
        page_key = f"{widget_key}_page"
        current_page = st.session_state.get(page_key, 0)
        current_page = min(current_page, total_pages - 1)

        nav_cols = st.columns([1, 3, 1])
        with nav_cols[0]:
            if st.button("◀ Prev", key=f"{widget_key}_prev", disabled=current_page == 0):
                current_page = max(0, current_page - 1)
                st.session_state[page_key] = current_page
                st.rerun()
        with nav_cols[2]:
            if st.button("Next ▶", key=f"{widget_key}_next", disabled=current_page >= total_pages - 1):
                current_page = min(total_pages - 1, current_page + 1)
                st.session_state[page_key] = current_page
                st.rerun()
        with nav_cols[1]:
            start_row = current_page * page_size + 1
            end_row = min((current_page + 1) * page_size, total_rows)
            st.caption(f"Showing {start_row}–{end_row} of {total_rows}")

        row_start = current_page * page_size
        row_end = row_start + page_size

        if is_styler:
            page_data = display_data.data.iloc[row_start:row_end]
            page_display = page_data.style
        else:
            page_display = display_data.iloc[row_start:row_end]

        visible_rows = min(page_size, total_rows - row_start)
        computed_height = config.get("height", min(35 * visible_rows + 45, 1800))

    # Render
    return st.dataframe(
        page_display,
        width="stretch",
        height=computed_height,
        hide_index=True,
        column_config=final_col_config,
        column_order=final_column_order,
        on_select="rerun",
        selection_mode=selection_mode,
        key=widget_key,
    )
