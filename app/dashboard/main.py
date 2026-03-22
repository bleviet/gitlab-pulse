"""Main Streamlit Dashboard Entry Point.

GitLabInsight Layer 3 Presentation Layer.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image

# Load environment variables
load_dotenv()

from app.dashboard.data_loader import (
    filter_by_context,
    filter_by_date_range,
    filter_by_milestone,
    filter_by_team,
    load_quality_issues,
    load_valid_issues,
)
from app.dashboard.views.overview import render_overview
from app.processor.rule_loader import RuleLoader
from app.dashboard.sidebar import render_sidebar
from app.dashboard.theme import apply_rule_color_overrides, get_global_css

_FAVICON = Image.open(Path(__file__).parent.parent / "static" / "favicon.png")

# Page configuration
st.set_page_config(
    page_title="GitLabInsight",
    page_icon=_FAVICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Global CSS: only residual styling not covered by config.toml theming
st.markdown(get_global_css(), unsafe_allow_html=True)
from app.dashboard.theme import inject_theme_watcher
inject_theme_watcher()


def _exit_edit_mode():
    """Callback to exit edit mode and reset toggle."""
    st.session_state["edit_mode"] = False
    st.session_state["edit_mode_toggle"] = False

def _render_custom_widget(
    widget_id: str,
    widget_type: str,
    filtered_df,
    quality_df,
    edit_mode: bool,
    layout_data: dict,
    WidgetRegistry,
    remove_widget_from_layout
) -> None:
    """Helper function to render a widget in Custom view."""
    if edit_mode:
        col_content, col_remove = st.columns([11, 1])
        with col_remove:
            if st.button("✕", key=f"remove_{widget_id}", help="Remove widget"):
                layout_data = remove_widget_from_layout(layout_data, widget_id)
                st.session_state["layout_data"] = layout_data
                st.rerun()
    else:
        col_content = st.container()

    with col_content:
        with st.container(border=True):
            try:
                renderer = WidgetRegistry.get_renderer(widget_type)
                config = {"key": widget_id}
                if widget_type in ["kpi_quality_score", "chart_quality_gauge"]:
                    renderer(filtered_df, quality_df, config)
                else:
                    renderer(filtered_df, config)
            except Exception as e:
                st.error(f"Error rendering {widget_type}: {e}")


def main() -> None:
    """Main dashboard entry point."""
    # Load data
    valid_df = load_valid_issues()
    quality_df = load_quality_issues()

    # Load rules to get color overrides
    rule_loader = RuleLoader()
    # Try to find default team rule, otherwise use first available or empty default
    default_rule = None
    for rule in rule_loader.rules.values():
        if rule.team == "default":
            default_rule = rule
            break

    if not default_rule:
        # Fallback: try first available rule, else empty default
        default_rule = next(iter(rule_loader.rules.values()), rule_loader.get_default_rule())

    apply_rule_color_overrides(default_rule.colors)

    # --- Early Bidirectional Sync Logic ---
    # Must update sidebar state BEFORE render_sidebar instantiates the widget
    if "timeline_reset_counter" not in st.session_state:
        st.session_state.timeline_reset_counter = 0

    current_layout_name = st.session_state.get("current_layout", "default")
    # Need to verify if we are in custom view or similar?
    # Just checking the active layout is safer.

    # Lazy load layout to check for timeline interactions
    from app.dashboard.engine import load_layout
    try:
        # Avoid full load overhead if possible, but load_layout is cached/fast usually
        pre_layout_data = st.session_state.get("layout_data") or load_layout(current_layout_name)
    except Exception:
        pre_layout_data = {}

    if pre_layout_data and "layout" in pre_layout_data:
        t_counter = st.session_state.timeline_reset_counter
        t_suffix = f"_{t_counter}"

        for item in pre_layout_data["layout"]:
            if item.get("type") == "chart_milestone_timeline":
                w_key = f"{item['i']}{t_suffix}"

                # Check for new selection
                if w_key in st.session_state:
                    new_selection = st.session_state[w_key]
                    last_selection = st.session_state.get(f"last_selection_{w_key}")

                    # Detect change
                    # Streamlit selection is a dict, comparison works if structurally same
                    if new_selection != last_selection:
                         st.session_state[f"last_selection_{w_key}"] = new_selection

                         # Extract milestone details
                         if new_selection and new_selection.get("selection", {}).get("points"):
                             points = new_selection["selection"]["points"]
                             if points:
                                 try:
                                     sel_ms = points[0]["customdata"][2]
                                     # Update Sidebar State
                                     st.session_state["sidebar_milestone_selector"] = sel_ms
                                     # Note: We don't need to rerun here, as we are before render_sidebar
                                 except (IndexError, KeyError):
                                     pass

    # Drain pending milestone selection from overview timeline (must happen before
    # render_sidebar instantiates the sidebar_milestone_selector widget)
    if "overview_milestone_pending" in st.session_state:
        st.session_state["sidebar_milestone_selector"] = st.session_state.pop("overview_milestone_pending")
    elif "overview_milestone_reset" in st.session_state:
        st.session_state.pop("overview_milestone_reset")
        st.session_state["sidebar_milestone_selector"] = "All"

    # Render sidebar and get filters
    filters = render_sidebar(valid_df)

    # Apply filters
    # Note: filter_by_* return new DataFrames via boolean indexing, so no
    # defensive .copy() is needed — the input is never mutated.
    filtered_df = valid_df
    pre_milestone_df = valid_df
    if not filtered_df.empty:
        filtered_df = filter_by_team(filtered_df, filters["team"])
        filtered_df = filter_by_context(filtered_df, filters["context"])
        # Save df before milestone filter — overview timeline needs all milestones
        pre_milestone_df = filtered_df
        filtered_df = filter_by_milestone(filtered_df, filters["milestone"])
        filtered_df = filter_by_date_range(
            filtered_df,
            filters["start_date"],
            filters["end_date"],
        )

    # Page navigation
    pages = {
        "📊 Overview": "overview",
        "🎨 Custom": "custom",
    }

    # Conditionally add Admin tab
    if st.session_state.get("is_admin"):
        pages["⚡ Admin"] = "admin"

    # --- MAIN NAVIGATION (Persistent Radio Button) ---
    # We use st.radio with 'horizontal' to mimic a tab bar but with state persistence

    # Ensure current page is valid
    current_page = st.session_state.get("current_page", list(pages.keys())[0])
    if current_page not in pages:
        current_page = list(pages.keys())[0]
        st.session_state.current_page = current_page

    selected_page = st.radio(
        "Navigation",
        options=list(pages.keys()),
        index=list(pages.keys()).index(current_page),
        horizontal=True,
        label_visibility="collapsed",
        key="main_nav_radio"
    )

    # Update session state if changed
    if selected_page != st.session_state.get("current_page"):
        st.session_state.current_page = selected_page
        st.rerun()

    # Dynamic rendering based on selection
    view_id = pages[selected_page]

    # Clear overview dialog state when navigating away so it never persists across views
    if view_id != "overview":
        st.session_state["show_issue_dialog"] = False
        st.session_state["selected_issue_url"] = ""
        st.session_state["show_filtered_issues_dialog"] = False
        st.session_state["filtered_issues_stage"] = None
        st.session_state["filtered_issues_state"] = None
        
        # Clear any retained chart selection state
        for key in list(st.session_state.keys()):
            if key.startswith("prev_sel_"):
                del st.session_state[key]

    if view_id == "overview":
        # Overview is now the Flow view (Value Stream)
        # Extract stage descriptions
        stage_descriptions = {
            stage.name: stage.description
            for stage in default_rule.workflow.stages
            if hasattr(stage, "description")
        }
        render_overview(
            filtered_df,
            quality_df=quality_df,
            stage_descriptions=stage_descriptions,
            timeline_df=pre_milestone_df,
            highlight_milestone=filters["milestone"],
        )
    elif view_id == "custom":
        # Custom view using layout-based widget rendering
        from app.dashboard.engine import load_layout, save_layout, remove_widget_from_layout
        from app.dashboard.registry import WidgetRegistry

        current_layout = st.session_state.get("current_layout", "default")
        layout_data = st.session_state.get("layout_data") or load_layout(current_layout)
        edit_mode = st.session_state.get("edit_mode", False)

        # Sync layout positions from streamlit-elements internal state
        internal_key = "streamlit_elements.core.frame.elements_frame.dashboard_grid"
        if edit_mode and internal_key in st.session_state:
            try:
                import json
                internal_state_str = st.session_state[internal_key]
                if isinstance(internal_state_str, str):
                    internal_data = json.loads(internal_state_str)
                    # Find the updated_layout in the nested structure
                    for frame_key, frame_data in internal_data.items():
                        if isinstance(frame_data, dict) and "updated_layout" in frame_data:
                            updated_positions = frame_data["updated_layout"]
                            if updated_positions:
                                # Merge updated positions with widget types
                                original_items = layout_data.get("layout", [])
                                merged_layout = []
                                for updated_item in updated_positions:
                                    item_id = str(updated_item.get("i", ""))
                                    original = next((x for x in original_items if str(x["i"]) == item_id), None)
                                    if original:
                                        merged_layout.append({
                                            "i": item_id,
                                            "x": int(updated_item.get("x", 0)),
                                            "y": int(updated_item.get("y", 0)),
                                            "w": int(updated_item.get("w", 6)),
                                            "h": int(updated_item.get("h", 4)),
                                            "type": original["type"]
                                        })
                                if merged_layout:
                                    layout_data["layout"] = merged_layout
                                    st.session_state["layout_data"] = layout_data
                            break
            except Exception as e:
                st.warning(f"Could not parse layout state: {e}")

        # Header with edit mode controls
        col1, col2, col3 = st.columns([6, 1, 1])
        with col1:
            st.header(f"🎨 {layout_data.get('name', current_layout)}")
        if edit_mode:
            with col2:
                if st.button("💾 Save", use_container_width=True):
                    save_layout(current_layout, layout_data)
                    st.success("Layout saved!")
            with col3:
                st.button("❌ Exit Edit", use_container_width=True, on_click=_exit_edit_mode)

        if edit_mode:
            st.info("🔧 Edit Mode: Drag widgets to rearrange. Resize using handles. Add new from sidebar.")

        # Render Grid Engine
        from app.dashboard.engine import render_grid

        # --- Bidirectional Sync Logic for Milestone Timeline ---
        current_milestone_filter = filters["milestone"]
        last_milestone_filter = st.session_state.get("last_milestone_filter")

        # Detect Sidebar Change -> Reset Timeline Selection
        if current_milestone_filter != last_milestone_filter:
            if last_milestone_filter is not None: # Skip initial load
                st.session_state.timeline_reset_counter += 1
            st.session_state.last_milestone_filter = current_milestone_filter

        timeline_reset_counter = st.session_state.timeline_reset_counter
        key_suffix = f"_{timeline_reset_counter}"

        # Pass sidebar selection to highlighting
        global_config = {
            "highlight_milestone": current_milestone_filter,
        }

        # Prepare overrides for filter source widgets
        # They should see the data BEFORE the interactive filter they triggered
        widget_overrides = {}

        # Check for interactive filters
        if layout_data and "layout" in layout_data:
            for item in layout_data["layout"]:
                # Milestone Timeline Logic
                if item.get("type") == "chart_milestone_timeline":
                    widget_key = f"{item['i']}{key_suffix}" # Use suffixed key
                    if widget_key in st.session_state:
                         selection = st.session_state[widget_key]
                         if selection and selection.get("selection", {}).get("points"):
                             points = selection["selection"]["points"]
                             if points:
                                 try:
                                     # customdata[2] is the milestone title
                                     selected_milestone = points[0]["customdata"][2]

                                     # Isolate the source widget to show original context
                                     widget_overrides[item["i"]] = filtered_df.copy() # Use original ID for overrides (engine maps it)
                                     filtered_df = filter_by_milestone(filtered_df, selected_milestone)
                                 except (IndexError, KeyError):
                                     pass

                # Stage Distribution Logic
                elif item.get("type") == "chart_stage_distribution":
                    # Stage distribution doesn't use the reset suffix mechanism yet, so use base key
                    # Or should we apply suffix to all? engine applies suffix to all.
                    # So we must use suffixed key to check state.
                    widget_key = f"{item['i']}{key_suffix}"
                    if widget_key in st.session_state:
                         selection = st.session_state[widget_key]
                         if selection and selection.get("selection", {}).get("points"):
                             selected_points = selection["selection"]["points"]
                             masks = []
                             for point in selected_points:
                                 # px.bar horizontal: y is stage
                                 stage = point.get("y")
                                 # customdata[0] is severity
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
                                 # Store current DF state before applying this specific filter
                                 # So the chart itself doesn't filter out its own bars
                                 widget_overrides[item["i"]] = filtered_df.copy() # Use original ID

                                 final_mask = pd.Series(False, index=filtered_df.index)
                                 for m in masks:
                                     final_mask |= m
                                 filtered_df = filtered_df[final_mask]

        updated_layout = render_grid(
            filtered_df,
            layout_data,
            edit_mode,
            quality_df=quality_df,
            widget_data_overrides=widget_overrides,
            key_suffix=key_suffix,
            global_config=global_config
        )
        if updated_layout is not None:
            layout_data["layout"] = updated_layout
            st.session_state["layout_data"] = layout_data
            st.rerun()


    elif view_id == "admin":
        from app.dashboard.views.admin import render_admin_view
        render_admin_view()


if __name__ == "__main__":
    main()
