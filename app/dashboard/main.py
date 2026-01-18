"""Main Streamlit Dashboard Entry Point.

GitLabInsight Layer 3 Presentation Layer.
"""

import streamlit as st

from app.dashboard.data_loader import (
    filter_by_date_range,
    filter_by_team,
    load_quality_issues,
    load_valid_issues,
)
from app.dashboard.pages.aging import render_aging
from app.dashboard.pages.hygiene import render_hygiene
from app.dashboard.pages.overview import render_overview
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
        filtered_df = filter_by_date_range(
            filtered_df,
            filters["start_date"],
            filters["end_date"],
        )

    # Page navigation
    pages = {
        "📊 Overview": "overview",
        "⏱️ Aging": "aging",
        "🧹 Hygiene": "hygiene",
    }

    # Tabs for navigation
    tabs = st.tabs(list(pages.keys()))

    with tabs[0]:
        render_overview(filtered_df)

    with tabs[1]:
        render_aging(filtered_df)

    with tabs[2]:
        render_hygiene(filtered_df, quality_df)


if __name__ == "__main__":
    main()
