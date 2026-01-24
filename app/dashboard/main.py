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
                if st.button("❌ Exit Edit", use_container_width=True):
                    st.session_state["edit_mode"] = False
                    st.rerun()

        if edit_mode:
            st.info("🔧 Edit Mode: Use the Widget Toolbox in sidebar to add widgets. Click ✕ to remove.")

        # Render widgets from layout
        layout_items = layout_data.get("layout", [])

        if not layout_items:
            st.info("No widgets in this view. Enable Edit Mode and use the Widget Toolbox to add widgets.")
        else:
            # Sort by y position (row), then x position
            sorted_items = sorted(layout_items, key=lambda x: (x.get("y", 0), x.get("x", 0)))

            # Two-pass rendering for interactive filtering:
            # Pass 1: Render charts first and capture selection state
            # Pass 2: Render tables with filtered data

            chart_widgets = [i for i in sorted_items if i.get("type", "").startswith("chart_")]
            table_widgets = [i for i in sorted_items if i.get("type", "").startswith("table_")]
            other_widgets = [i for i in sorted_items if not i.get("type", "").startswith(("chart_", "table_"))]

            # Track selection state for cross-widget filtering
            stage_filter = None

            # Render KPIs and other widgets first
            for item in other_widgets:
                widget_id = item["i"]
                widget_type = item.get("type", "unknown")
                _render_custom_widget(widget_id, widget_type, filtered_df, quality_df, edit_mode, layout_data, WidgetRegistry, remove_widget_from_layout)

            # Render charts and capture selections
            for item in chart_widgets:
                widget_id = item["i"]
                widget_type = item.get("type", "unknown")

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
                            # Charts return selection state
                            selection = renderer(filtered_df, config)

                            # Capture stage filter from stage_distribution chart
                            if widget_type == "chart_stage_distribution" and selection:
                                points = selection.get("selection", {}).get("points", [])
                                if points:
                                    stages = [p.get("y") for p in points if p.get("y")]
                                    if stages:
                                        stage_filter = stages
                        except Exception as e:
                            st.error(f"Error rendering {widget_type}: {e}")

            # Apply filter if chart selection was made
            table_df = filtered_df.copy()
            if stage_filter and "stage" in table_df.columns:
                table_df = table_df[table_df["stage"].isin(stage_filter)]
                st.caption(f"🔍 Filtered by stage: {', '.join(stage_filter)}")

            # Render tables with potentially filtered data
            for item in table_widgets:
                widget_id = item["i"]
                widget_type = item.get("type", "unknown")

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
                            renderer(table_df, config)
                        except Exception as e:
                            st.error(f"Error rendering {widget_type}: {e}")


    elif view_id == "admin":
        from app.dashboard.views.admin import render_admin_view
        render_admin_view()


if __name__ == "__main__":
    main()
