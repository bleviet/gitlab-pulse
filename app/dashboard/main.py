"""Main Streamlit Dashboard Entry Point.

GitLabInsight Layer 3 Presentation Layer.
"""

import streamlit as st
from dotenv import load_dotenv

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
from app.dashboard.views.aging import render_aging
from app.dashboard.views.overview import render_overview
from app.dashboard.views.hygiene import render_hygiene
from app.dashboard.views.stats import render_stats_view
from app.processor.rule_loader import RuleLoader
from app.dashboard.sidebar import render_sidebar

# Page configuration
st.set_page_config(
    page_title="GitLabInsight",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for consistent styling
st.markdown("""
<style>
    /* Metric styling moved to app/dashboard/components.py */
</style>
""", unsafe_allow_html=True)


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

    colors = default_rule.colors

    # Render sidebar and get filters
    filters = render_sidebar(valid_df)

    # Apply filters
    filtered_df = valid_df.copy()
    if not filtered_df.empty:
        filtered_df = filter_by_team(filtered_df, filters["team"])
        filtered_df = filter_by_context(filtered_df, filters["context"])
        filtered_df = filter_by_milestone(filtered_df, filters["milestone"])
        filtered_df = filter_by_date_range(
            filtered_df,
            filters["start_date"],
            filters["end_date"],
        )

    # Page navigation
    pages = {
        "📊 Overview": "overview",
        "🚀 Release": "release",
        "⚖️ Capacity": "capacity",
        "📈 Stats": "stats",
        "⏱️ Aging": "aging",
        "🧹 Hygiene": "hygiene",
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

    if view_id == "overview":
        # Overview is now the Flow view (Value Stream)
        # Extract stage descriptions
        stage_descriptions = {
            stage.name: stage.description
            for stage in default_rule.workflow.stages
            if hasattr(stage, "description")
        }
        render_overview(filtered_df, colors=colors, stage_descriptions=stage_descriptions)
    elif view_id == "stats":
        # Stats is the old overview (KPIs, Burnup)
        render_stats_view(filtered_df, colors=colors)
    elif view_id == "capacity":
        # Pass capacity config
        capacity_config = default_rule.capacity.model_dump()
        from app.dashboard.views.capacity import render_capacity_view
        render_capacity_view(filtered_df, colors=colors, capacity_config=capacity_config)
    elif view_id == "release":
        from app.dashboard.views.release import render_release_view
        render_release_view(filtered_df)
    elif view_id == "aging":
        render_aging(filtered_df, colors=colors)
    elif view_id == "hygiene":
        render_hygiene(filtered_df, quality_df, colors=colors)
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
        updated_layout = render_grid(filtered_df, layout_data, edit_mode, quality_df=quality_df)
        if updated_layout is not None:
            layout_data["layout"] = updated_layout
            st.session_state["layout_data"] = layout_data
            st.rerun()


    elif view_id == "admin":
        from app.dashboard.views.admin import render_admin_view
        render_admin_view()


if __name__ == "__main__":
    main()
