"""Overview Page (Value Stream) for Layer 3 Dashboard.

Visualizes flow efficiency, bottlenecks, and aging.
Refactored to use Widget Registry where applicable.
"""

import pandas as pd
import streamlit as st

from app.dashboard.utils import sort_hierarchy
from app.dashboard.widgets import charts, features, kpis, tables


def render_overview(
    df: pd.DataFrame,
    stage_descriptions: dict[str, str] | None = None
) -> None:
    """Render the Overview (Flow) page.

    Args:
        df: Filtered DataFrame with valid issues
        stage_descriptions: Optional mapping of stage names to description strings
    """
    if df.empty:
        st.warning("No data available.")
        return

    unique_df = df.drop_duplicates(subset=["id"]) if "id" in df.columns else df

    # Top Row: Metrics (Use unique issues) - via widget
    kpis.flow_metrics(unique_df)

    # Side-by-side layout: issue list on the left, chart on the right
    col_list, col_chart = st.columns([1, 1], gap="medium")

    with col_chart, st.expander("Visual Analysis", expanded=True):
        # Stage distribution rotated 90° CCW (vertical bars: stages on x-axis)
        stage_selection = charts.stage_distribution(
            unique_df,
            config={
                "stage_descriptions": stage_descriptions,
                "key": "flow_chart_stage_dist",
                "orientation": "v",
            }
        )

    # Apply interactive filters (apply to original DF to allow exploring contexts)
    filtered_df = df.copy()

    if stage_selection and stage_selection.get("selection", {}).get("points"):
        selected_points = stage_selection["selection"]["points"]
        masks = []
        for point in selected_points:
            # Vertical chart: x=stage (string), y=count (number)
            # Detect stage value robustly: it is the string dimension
            x_val = point.get("x")
            y_val = point.get("y")
            stage = x_val if isinstance(x_val, str) else y_val

            severity = point.get("customdata", [None])[0]

            mask = (filtered_df["stage"] == stage)
            if severity:
                if severity == "Unset":
                    mask &= (
                        filtered_df["severity"].isna() |
                        (filtered_df["severity"].astype(str).str.strip().str.lower().isin(["unset", "none", "nan", "<na>", ""]))
                    )
                else:
                    mask &= (filtered_df["severity"].astype(str).str.strip().str.lower() == severity.lower())

            masks.append(mask)

        if masks:
            final_mask = pd.Series(False, index=filtered_df.index)
            for m in masks:
                final_mask |= m
            filtered_df = filtered_df[final_mask]

    with col_list, st.expander("📋 Issue List", expanded=True):
        _render_issue_detail_grid(filtered_df, compact=True)




def _render_issue_detail_grid(df: pd.DataFrame, compact: bool = False) -> None:
    """Render unified issue detail grid with drill-down filters.

    Args:
        df: DataFrame of issues to display
        compact: When True, show only title and assignee columns (used in
            side-by-side layout where the chart provides stage/priority context).
    """

    # --- Column Filters (Expandable) ---
    with st.expander("🔍 Filters", expanded=False):
        # Row 1: Title search (full width)
        title_search = st.text_input(
            "Search Title",
            placeholder="Type to search issue titles...",
            key="filter_title"
        )

        # Row 2: Multiselect filters (3 columns)
        filter_cols_row1 = st.columns(3)

        # 1. Stage Filter
        with filter_cols_row1[0]:
            available_stages = sorted(
                df["stage"].unique(),
                key=lambda s: df[df["stage"] == s]["stage_order"].min()
            )
            selected_stages = st.multiselect(
                "Stage",
                options=available_stages,
                default=[],
                key="filter_stage"
            )

        # 2. Priority Filter
        with filter_cols_row1[1]:
            if "severity" in df.columns:
                available_priorities = sorted(df["severity"].dropna().unique().tolist())
                selected_priorities = st.multiselect(
                    "Priority",
                    options=available_priorities,
                    default=[],
                    key="filter_priority"
                )
            else:
                selected_priorities = []

        # 3. Context Filter
        with filter_cols_row1[2]:
            if "context" in df.columns:
                available_contexts = sorted(df["context"].dropna().unique().tolist())
                selected_contexts = st.multiselect(
                    "Context",
                    options=available_contexts,
                    default=[],
                    key="filter_context"
                )
            else:
                selected_contexts = []

        # Row 3: Milestone and Assignee (2 columns)
        filter_cols_row2 = st.columns(2)

        # 4. Milestone Filter
        with filter_cols_row2[0]:
            if "milestone" in df.columns:
                available_milestones = sorted(df["milestone"].dropna().unique().tolist())
                selected_milestones = st.multiselect(
                    "Milestone",
                    options=available_milestones,
                    default=[],
                    key="filter_milestone"
                )
            else:
                selected_milestones = []

        # 5. Assignee Filter
        with filter_cols_row2[1]:
            if "assignee" in df.columns:
                available_assignees = sorted(df["assignee"].dropna().unique().tolist())
                selected_assignees = st.multiselect(
                    "Assignee",
                    options=available_assignees,
                    default=[],
                    key="filter_assignee"
                )
            else:
                selected_assignees = []

    # --- Apply Filters ---
    display_df = df.copy()

    # Title search (case-insensitive)
    if title_search:
        display_df = display_df[display_df["title"].str.contains(title_search, case=False, na=False)]

    if selected_stages:
        display_df = display_df[display_df["stage"].isin(selected_stages)]

    if selected_priorities:
        display_df = display_df[display_df["severity"].isin(selected_priorities)]

    if selected_contexts:
        display_df = display_df[display_df["context"].isin(selected_contexts)]

    if selected_milestones:
        display_df = display_df[display_df["milestone"].isin(selected_milestones)]

    if selected_assignees:
        display_df = display_df[display_df["assignee"].isin(selected_assignees)]

    # Sort by Hierarchy (Parent -> Child) or Staleness
    if "parent_id" in display_df.columns:
        display_df = sort_hierarchy(display_df, parent_col="parent_id", id_col="iid", title_col="title")
    else:
        display_df = display_df.sort_values("days_in_stage", ascending=False)

    # Select Columns (keep 'id' for AI status lookup, 'iid' for numeric sorting)
    cols_to_show = [
        "id", "iid", "web_url", "title", "stage", "days_in_stage",
        "severity", "context", "milestone", "assignee",
    ]
    cols = [c for c in cols_to_show if c in display_df.columns]

    display_df = display_df[cols]

    # Reset index to ensure uniqueness for styling
    display_df = display_df.reset_index(drop=True)

    # Add AI Summary Status Column
    from pathlib import Path
    ai_storage_path = Path("data/ai")

    def check_summary_status(issue_id):
        """Check if an AI summary exists for the issue."""
        if pd.isna(issue_id):
            return "✨"
        summary_file = ai_storage_path / f"chat_{int(issue_id)}.parquet"
        if summary_file.exists():
            return "📝"
        return "✨"

    display_df.insert(0, "ai_status", display_df["id"].apply(check_summary_status))

    # Combine web_url + iid + title into a single clickable "title" column
    if "web_url" in display_df.columns and "title" in display_df.columns:
        iid_part = display_df["iid"].astype(str) if "iid" in display_df.columns else "?"
        display_df["title"] = (
            display_df["web_url"]
            + "#"
            + iid_part
            + " - "
            + display_df["title"].fillna("")
        )
        if "iid" in display_df.columns:
            display_df = display_df.drop(columns=["iid"])

    column_config = {
        "ai_status": st.column_config.TextColumn(
            "AI",
            width=40,
            help="📝 = Has AI summary | ✨ = No summary yet"
        ),
        "title": st.column_config.LinkColumn(
            "Title",
            display_text=r"#(.+)$",
            width="large",
            help="Click to open in GitLab",
        ),
        "assignee": st.column_config.TextColumn("Assignee", width="small"),
        "stage": st.column_config.TextColumn("Stage", width="small"),
        "days_in_stage": st.column_config.NumberColumn(
            "Days in Stage",
            help="Days since last update in this stage",
            format="%d days",
        ),
        "severity": st.column_config.TextColumn("Priority", width="small"),
        "context": st.column_config.TextColumn("Context", width="small"),
        "milestone": st.column_config.TextColumn("Milestone", width="medium"),
    }

    # Apply styling if Context column exists
    styler = None
    if "context" in display_df.columns:
        from app.dashboard.data_loader import load_labels
        label_styles = load_labels()

        def highlight_context(val):
            if not isinstance(val, str):
                return None
            style = label_styles.get(val)
            if style:
                bg_color = style.get("color", "#FFFFFF")
                text_color = style.get("text_color", "#000000")
                return f'background-color: {bg_color}; color: {text_color}'
            return None

        styler = display_df.style.map(highlight_context, subset=["context"])

    # Compact mode: title + assignee only (stage/priority context via chart clicks)
    if compact:
        column_order = ["ai_status", "title", "assignee"]
    else:
        column_order = ["ai_status", "title", "stage", "days_in_stage", "severity", "milestone", "assignee"]
        if "context" in display_df.columns:
            column_order.insert(2, "context")

    # --- AI PANEL LOGIC ---
    selection_state = st.session_state.get("issue_drilldown_table", {})
    if hasattr(selection_state, "selection"):
        selection_state = selection_state.selection
    selected_indices = getattr(selection_state, "rows", [])
    if not selected_indices and isinstance(selection_state, dict):
        selected_indices = selection_state.get("rows", [])

    has_selection = len(selected_indices) > 0

    # Persist selected issue for AI panel (survives sorting/rerun)
    if has_selection:
        _page = st.session_state.get("issue_drilldown_table_page", 0)
        _page_size = st.session_state.get("issue_drilldown_table_page_size", 25)
        _offset = 0 if isinstance(_page_size, str) else _page * int(_page_size)
        selected_idx = selected_indices[0] + _offset
        if selected_idx < len(display_df):
            selected_row = display_df.iloc[selected_idx]
            st.session_state.selected_issue_url = selected_row.get("web_url", "")
            st.session_state.selected_issue_title = selected_row.get("title", "")

    if "show_ai_panel" not in st.session_state:
        st.session_state.show_ai_panel = False

    if has_selection and not st.session_state.show_ai_panel:
        st.session_state.show_ai_panel = True

    has_persisted_selection = st.session_state.get("selected_issue_url", "") != ""

    # Header row with toggle
    col_header, col_toggle = st.columns([4, 1])
    with col_toggle:
        if st.session_state.show_ai_panel and st.button("✕ Close AI", use_container_width=True, help="Hide AI Assistant panel"):
            st.session_state.show_ai_panel = False
            st.session_state.selected_issue_url = ""
            st.session_state.selected_issue_title = ""
            st.rerun()

    is_split_view = st.session_state.show_ai_panel and has_persisted_selection

    def render_table(cols):
        st.caption("Select an issue to view AI insights.")
        tables.issue_detail_grid(
            styler if styler is not None else display_df,
            config={
                "column_config": column_config,
                "column_order": cols,
                "selection_mode": "single-row",
                "key": "issue_drilldown_table",
                "minimize_columns": False,
                "enable_filters": False
            }
        )

    if is_split_view:
        # In compact mode the AI panel uses the same minimal columns
        ai_column_order = ["ai_status", "title"] if compact else ["ai_status", "title", "stage", "severity", "days_in_stage"]
        col_left, col_right = st.columns([1.5, 1], gap="medium")
        with col_left:
            render_table(ai_column_order)
        with col_right:
            features.ai_assistant(df, display_df)
    else:
        render_table(column_order)
