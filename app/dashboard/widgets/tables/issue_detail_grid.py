"""Issue Detail Grid Table Widget."""

from typing import Any

import pandas as pd
import streamlit as st
from pandas.io.formats.style import Styler

from app.dashboard.theme import (
    FONT_BODY,
    get_active_theme_mode,
    get_palette,
    get_streamlit_theme_color,
)
from app.dashboard.utils import sort_hierarchy


def _table_theme() -> dict[str, str]:
    """Return table-specific colors derived from the active theme."""
    mode = get_active_theme_mode()
    if mode == "dark":
        bg      = get_streamlit_theme_color("backgroundColor",          "#050811")
        row_alt = get_streamlit_theme_color("secondaryBackgroundColor", "#0c1123")
        text    = get_streamlit_theme_color("textColor",                "#ffffff")
        muted   = "#8a9bb2"
    else:
        bg      = get_streamlit_theme_color("backgroundColor",          "#f8f9fc")
        row_alt = get_streamlit_theme_color("secondaryBackgroundColor", "#ffffff")
        text    = get_streamlit_theme_color("textColor",                "#0d1120")
        muted   = "#5a6a82"
    return {"bg": bg, "row_alt": row_alt, "text": text, "muted": muted}


def _apply_base_cell_styles(styler: Styler, bg: str, text: str) -> Styler:
    """Apply background and text colour to every cell so they match the theme."""
    return styler.set_properties(**{
        "background-color": bg,
        "color": text,
        "font-family": FONT_BODY,
        "font-size": "0.83rem",
    })


def _apply_zebra_stripes(styler: Styler, stripe_color: str, text: str) -> Styler:
    """Apply zebra-striping styles to a Styler object."""
    dataframe = styler.data

    def _zebra(_: pd.DataFrame) -> pd.DataFrame:
        styles = pd.DataFrame("", index=dataframe.index, columns=dataframe.columns)
        styles.iloc[1::2, :] = (
            f"background-color: {stripe_color}; color: {text};"
        )
        return styles

    return styler.apply(_zebra, axis=None)


def issue_detail_grid(
    data: pd.DataFrame | Styler,
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
            - zebra_stripes: bool (default True)
            - zebra_color: CSS color for zebra rows
            - key: widget key

    Returns:
        Selection object from st.dataframe
    """
    config = config or {}
    title = config.get("title")
    widget_key = config.get("key", "issue_detail_grid")
    selection_mode = config.get("selection_mode", "multi-row")
    default_page_size = config.get("page_size", 25)
    zebra_stripes = config.get("zebra_stripes", True)

    t = _table_theme()
    zebra_color = config.get("zebra_color") or t["row_alt"]

    if title:
        st.subheader(title)

    # Check if data is Styler
    is_styler = isinstance(data, Styler)

    # Column Renames (defined early so they are available inside the filter expander)
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
        "updated_at": "Last Update",
    }

    def map_col(c: str) -> str:
        return column_renames.get(c, c)

    # Track extra columns selected by the user via the Filters expander
    extra_cols_selected: list[str] = []

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
                            default=[],
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
                            default=[],
                            key=filter_key_type
                        )
                        if selected_types:
                            df = df[df["issue_type"].isin(selected_types)]

                # Additional Columns selector
                default_cols_raw = config.get(
                    "columns",
                    ["web_url", "title", "issue_type", "stage", "assignee", "priority", "milestone"],
                )
                optional_raw = [
                    c for c in column_renames
                    if c in df.columns and c not in default_cols_raw
                ]
                if optional_raw:
                    optional_display = [map_col(c) for c in optional_raw]
                    extra_key = f"{widget_key}_extra_cols"
                    extra_cols_selected = st.multiselect(
                        "Additional Columns",
                        options=optional_display,
                        default=[],
                        key=extra_key,
                        help="Add extra columns to the table view",
                    )

        # Column handling
        # User request: "The table should have the possiblity display all the issue details..."
        # We generally avoid hard-dropping columns.
    display_df = df.copy()

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

    # Get user config columns and map them
    user_cols_raw = config.get("columns", default_columns_raw)
    column_order = [map_col(c) for c in user_cols_raw if c in df.columns]

    # Append any extra columns the user selected in the Filters expander
    for ecol in extra_cols_selected:
        if ecol not in column_order:
            column_order.append(ecol)

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

        button_cols = st.columns([1, 1])
        with button_cols[0]:
            if st.button(
                "◀ Prev",
                use_container_width=True,
                key=f"{widget_key}_prev",
                disabled=current_page == 0,
            ):
                current_page = max(0, current_page - 1)
                st.session_state[page_key] = current_page
                st.rerun()
        with button_cols[1]:
            if st.button(
                "Next ▶",
                use_container_width=True,
                key=f"{widget_key}_next",
                disabled=current_page >= total_pages - 1,
            ):
                current_page = min(total_pages - 1, current_page + 1)
                st.session_state[page_key] = current_page
                st.rerun()

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

    if zebra_stripes:
        if isinstance(page_display, Styler):
            page_display = _apply_base_cell_styles(page_display, t["bg"], t["text"])
            page_display = _apply_zebra_stripes(page_display, zebra_color, t["text"])
        else:
            styled = _apply_base_cell_styles(page_display.style, t["bg"], t["text"])
            page_display = _apply_zebra_stripes(styled, zebra_color, t["text"])
    elif isinstance(page_display, Styler):
        page_display = _apply_base_cell_styles(page_display, t["bg"], t["text"])
    else:
        page_display = _apply_base_cell_styles(page_display.style, t["bg"], t["text"])

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
