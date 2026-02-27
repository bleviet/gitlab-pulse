"""Overview Page (Value Stream) for Layer 3 Dashboard.

Visualizes flow efficiency, bottlenecks, and aging.
Refactored to use Widget Registry where applicable.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.utils import sort_hierarchy
from app.dashboard.widgets import kpis, charts, tables, features
from app.dashboard.theme import PALETTE as COLORS


def render_overview(
    df: pd.DataFrame,
    colors: dict[str, str] | None = None,
    stage_descriptions: dict[str, str] | None = None
) -> None:
    """Render the Overview (Flow) page.

    Args:
        df: Filtered DataFrame with valid issues
        colors: Optional dictionary of semantic colors to override defaults
        stage_descriptions: Optional mapping of stage names to description strings
    """
    if colors:
        COLORS.update(colors)

    # Filter out empty stages or irrelevant data if needed
    # But for flow, we usually want to see everything
    if df.empty:
        st.warning("No data available.")
        return

    # Deduplicate for global metrics and charts to avoid double counting
    # Multi-context issues appear as multiple rows in 'df' (one per context)
    # We want to count the issue only once for WIP, Efficiency, and Charts
    if "id" in df.columns:
        unique_df = df.drop_duplicates(subset=["id"])
    else:
        unique_df = df

    # Top Row: Metrics (Use unique issues) - via widget
    kpis.flow_metrics(unique_df)

    # Charts (Collapsible)
    with st.expander("Visual Analysis", expanded=True):
        chart_mode = st.radio(
            "Chart Mode",
            ["Work by Stage", "Days in Stage"],
            horizontal=True,
            label_visibility="collapsed",
            key="flow_chart_radio"
        )

        if chart_mode == "Work by Stage":
            # Use unique issues for stage distribution to show correct counts
            # Use shared widget with overview-specific key
            stage_selection = charts.stage_distribution(
                unique_df,
                config={
                    "stage_descriptions": stage_descriptions,
                    "key": "flow_chart_stage_dist",
                    "colors": colors
                }
            )
            aging_selection = None

        else:
            # Use unique issues for aging to show distinct items
            # Use shared widget with proper configuration
            aging_selection = charts.aging_boxplot(
                unique_df,
                config={
                    "key": "flow_chart_aging_box",
                    "filter_closed": True
                }
            )
            stage_selection = None

    # Apply interactive filters (Apply to original DF which allows exploring contexts)
    filtered_df = df.copy()

    # Filter by Stage Distribution Selection
    if stage_selection and stage_selection.get("selection", {}).get("points"):
        selected_points = stage_selection["selection"]["points"]
        # Extract filters: stage and severity
        # We perform an OR filter for multiple selected points
        masks = []
        for point in selected_points:
            # Point has customdata or y (stage) and legend group/color (severity)
            # px.bar with orientation h: y is stage, color is severity
            # customdata is likely needed to be robust
            stage = point.get("y")
            severity = point.get("customdata", [None])[0] # customdata[0] is severity if we add it

            mask = (filtered_df["stage"] == stage)
            if severity:
                 # Normalize severity for comparison to match the chart's logic
                 # The chart uses Title Case for all severities, and "Unset" for NaNs

                 if severity == "Unset":
                     # Match "Unset", NaNs, None, empty strings
                     mask &= (
                         filtered_df["severity"].isna() |
                         (filtered_df["severity"].astype(str).str.strip().str.lower().isin(["unset", "none", "nan", "<na>", ""]))
                     )
                 else:
                     # Match severity (case-insensitive to be safe)
                     mask &= (filtered_df["severity"].astype(str).str.strip().str.lower() == severity.lower())

            masks.append(mask)

        if masks:
            final_mask = pd.Series(False, index=filtered_df.index)
            for m in masks:
                final_mask |= m
            filtered_df = filtered_df[final_mask]

    # Filter by Aging Selection (Intersection with Stage Distribution chart)
    if aging_selection and aging_selection.get("selection", {}).get("points"):
        selected_points = aging_selection["selection"]["points"]
        # Aging chart: x=stage, y=days_in_stage, color=stage_type
        # We filter by stage (x). Days is continuous, so selecting a point usually implies interest in that item or stage.
        # But boxplots selection might be selecting outliers?
        # Let's assume selecting points filters by Stage of those points.
        selected_stages = {p.get("x") for p in selected_points}
        if selected_stages:
            filtered_df = filtered_df[filtered_df["stage"].isin(selected_stages)]

    # Detail grid (Collapsible)
    with st.expander("📋 Issue List", expanded=True):
        _render_issue_detail_grid(filtered_df)




def _render_issue_detail_grid(df: pd.DataFrame) -> None:
    """Render unified issue detail grid with drill-down filters."""

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

    # 3. Sort by Hierarchy (Parent -> Child) or Staleness
    # User requested hierarchical view.
    if "parent_id" in display_df.columns:
        # parent_id contains IID, so we must map to 'iid' column, not 'id'
        display_df = sort_hierarchy(display_df, parent_col="parent_id", id_col="iid", title_col="title")
    else:
        display_df = display_df.sort_values("days_in_stage", ascending=False)

    # 4. Select Columns (keep 'id' for AI status lookup, 'iid' for numeric sorting)
    cols_to_show = [
        "id", "iid", "web_url", "title", "stage", "days_in_stage", "severity", "context", "milestone", "assignee"
    ]
    # Filter columns that exist
    cols = [c for c in cols_to_show if c in display_df.columns]

    # 5. Configure Columns and Render
    display_df = display_df[cols]

    # Reset index to ensure uniqueness for styling (sort_hierarchy can cause duplicate indices with exploded contexts)
    display_df = display_df.reset_index(drop=True)

    # 6. Add AI Summary Status Column
    # Check which issues have existing AI summaries using the 'id' column directly
    from pathlib import Path
    ai_storage_path = Path("data/ai")

    def check_summary_status(issue_id):
        """Check if an AI summary exists for the issue."""
        if pd.isna(issue_id):
            return "✨"
        summary_file = ai_storage_path / f"chat_{int(issue_id)}.parquet"
        if summary_file.exists():
            return "📝"  # Has summary
        return "✨"  # No summary (generate)

    display_df.insert(0, "ai_status", display_df["id"].apply(check_summary_status))

    column_config = {
        "ai_status": st.column_config.TextColumn(
            "AI",
            width=40,
            help="📝 = Has AI summary | ✨ = No summary yet"
        ),
        "iid": st.column_config.NumberColumn(
            "IID",
            width=60,
            help="Issue IID (numeric for proper sorting)"
        ),
        "web_url": st.column_config.LinkColumn(
            "Link",
            display_text="🔗",
            width=40,
            help="Click to open in GitLab"
        ),
        "assignee": st.column_config.TextColumn("Assignee", width="small"),
        "stage": st.column_config.TextColumn("Stage", width="small"),
        "title": st.column_config.TextColumn("Title", width="large"),
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

    column_order = ["ai_status", "web_url", "iid", "title", "stage", "days_in_stage", "severity", "milestone", "assignee"]
    if "context" in display_df.columns:
        column_order.insert(6, "context")

    # --- AI PANEL LOGIC ---
    # Check if a row is selected - if so, auto-show split view
    
    selection_state = st.session_state.get("issue_drilldown_table", {})
    if hasattr(selection_state, "selection"):
        selection_state = selection_state.selection
    selected_indices = getattr(selection_state, "rows", [])
    if not selected_indices and isinstance(selection_state, dict):
        selected_indices = selection_state.get("rows", [])

    has_selection = len(selected_indices) > 0

    # Persist selected issue for AI panel (survives sorting/rerun)
    if has_selection:
        # Store the selected issue data in session state
        selected_idx = selected_indices[0]
        if selected_idx < len(display_df):
            selected_row = display_df.iloc[selected_idx]
            st.session_state.selected_issue_url = selected_row.get("web_url", "")
            st.session_state.selected_issue_title = selected_row.get("title", "")

    # Show/Hide AI Panel Toggle
    if "show_ai_panel" not in st.session_state:
        st.session_state.show_ai_panel = False

    # Auto-show AI panel when a row is selected
    if has_selection and not st.session_state.show_ai_panel:
        st.session_state.show_ai_panel = True

    # Determine if we have a persisted selection (even if current selection is lost due to sorting)
    has_persisted_selection = st.session_state.get("selected_issue_url", "") != ""

    # Header row with toggle
    col_header, col_toggle = st.columns([4, 1])
    with col_toggle:
        if st.session_state.show_ai_panel:
            if st.button("✕ Close AI", use_container_width=True, help="Hide AI Assistant panel"):
                st.session_state.show_ai_panel = False
                # Clear persisted selection when closing
                st.session_state.selected_issue_url = ""
                st.session_state.selected_issue_title = ""
                st.rerun()

    # Layout Logic - use persisted selection to maintain AI panel visibility
    is_split_view = st.session_state.show_ai_panel and has_persisted_selection

    # Helper for table rendering
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

    # Compact column order for split view (essential columns + Priority)
    if is_split_view:
        compact_column_order = ["ai_status", "web_url", "iid", "title", "stage", "severity", "days_in_stage"]
        # Split view: Side-by-side columns
        col_left, col_right = st.columns([1.5, 1], gap="medium")
        with col_left:
            render_table(compact_column_order)
        with col_right:
            features.ai_assistant(df, display_df)
    else:
        # Table only view - show all columns
        render_table(column_order)
