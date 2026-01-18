"""Main Streamlit Dashboard Entry Point.

GitLabInsight Layer 3 Presentation Layer.
"""

import streamlit as st

from app.dashboard.data_loader import (
    filter_by_context,
    filter_by_date_range,
    filter_by_team,
    load_quality_issues,
    load_valid_issues,
)
from app.dashboard.views.aging import render_aging
from app.dashboard.views.flow import render_flow_view
from app.dashboard.views.hygiene import render_hygiene
from app.dashboard.views.overview import render_overview
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
    .stMetric {
        background-color: var(--secondary-background-color);
        padding: 1rem;
        border-radius: 0.5rem;
    }
    .stMetric label {
        font-size: 0.875rem !important;
        color: var(--text-color) !important;
        opacity: 0.7;
    }
    .stMetric [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)


def main() -> None:
    """Main dashboard entry point."""
    # Load data
    valid_df = load_valid_issues()
    quality_df = load_quality_issues()

    # Render sidebar and get filters
    filters = render_sidebar(valid_df)

    # Apply filters
    filtered_df = valid_df.copy()
    if not filtered_df.empty:
        filtered_df = filter_by_team(filtered_df, filters["team"])
        filtered_df = filter_by_context(filtered_df, filters["context"])
        filtered_df = filter_by_date_range(
            filtered_df,
            filters["start_date"],
            filters["end_date"],
        )

    # Page navigation
    pages = {
        "📊 Overview": "overview",
        "🌊 Flow": "flow",
        "🚀 Release": "release",
        "⏱️ Aging": "aging",
        "🧹 Hygiene": "hygiene",
    }

    # Conditionally add Admin tab
    if st.session_state.get("is_admin"):
        pages["⚡ Admin"] = "admin"

    # Tabs for navigation
    tabs = st.tabs(list(pages.keys()))

    # Dynamic rendering
    for i, (page_name, view_id) in enumerate(pages.items()):
        with tabs[i]:
            if view_id == "overview":
                render_overview(filtered_df)
            elif view_id == "flow":
                render_flow_view(filtered_df)
            elif view_id == "release":
                from app.dashboard.views.release import render_release_view
                render_release_view(filtered_df)
            elif view_id == "aging":
                render_aging(filtered_df)
            elif view_id == "hygiene":
                render_hygiene(filtered_df, quality_df)
            elif view_id == "admin":
                from app.dashboard.views.admin import render_admin_view
                render_admin_view()


if __name__ == "__main__":
    main()
