"""Stats Page (Metrics Summary) for Layer 3 Dashboard.

KPI cards, burn-up chart, and distribution visualizations.
Refactored to use Widget Registry.
"""

import pandas as pd
import streamlit as st

from app.dashboard.registry import WidgetRegistry
from app.dashboard.widgets import kpis, charts


def render_stats_view(df: pd.DataFrame, colors: dict[str, str] | None = None) -> None:
    """Render the Stats (Metrics) page.

    Args:
        df: Filtered DataFrame with valid issues
        colors: Optional dictionary of semantic colors to override defaults
    """

    st.caption("Strategic view of project velocity and distribution")

    if df.empty:
        st.warning("No data available. Run the collector and processor first.")
        return

    # Top Row: KPI Cards (via Registry)
    kpis.stats_kpis(df)

    # Middle Row: Burn-up Chart (Collapsible)
    with st.expander("📈 Cumulative Flow by Type", expanded=True):
        charts.burnup_velocity(df)

    # Bottom Row: Distribution Charts (Collapsible)
    with st.expander("📊 Distribution Charts", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            charts.work_type_distribution(df)
        with col2:
            charts.status_donut(df)
