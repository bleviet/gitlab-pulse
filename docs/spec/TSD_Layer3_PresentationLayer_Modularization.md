Technical Specification: Layer 3 - Phase 1 ModularizationVersion: 1.0Context: This is the foundational refactoring required to enable the future "Dashboard Builder" (Architecture v2.0).Goal: Decouple the visualization logic from the page layout logic. Transform monolithic view files into a registry of independent, reusable widgets.1. Directory Structure ChangesWe will move visualization logic out of views/ and into a new widgets/ package.app/dashboard/
├── registry.py             # NEW: Central catalog of all available widgets
├── widgets/                # NEW: The Component Library
│   ├── __init__.py
│   ├── kpis.py             # Single-number metric cards
│   ├── charts.py           # Plotly charts (Burn-up, Boxplots)
│   └── tables.py           # Dataframes (Master-Detail, Lists)
└── views/
    ├── overview.py         # Refactored to use Registry
    └── ...
2. The Widget Interface (Contract)To ensure every component can eventually be dragged, dropped, and configured, they must all follow a strict Function Signature.2.1. The Standard SignatureEvery widget function must accept exactly these arguments:from typing import Optional, Dict, Any
import pandas as pd

def render_widget(data: pd.DataFrame, config: Optional[Dict[str, Any]] = None) -> None:
    """
    Renders a specific UI component using Streamlit.
    
    Args:
        data: The filtered Analytics DataFrame (Layer 2 output).
        config: Optional dictionary for customization (e.g., {"title": "My Chart", "height": 400}).
    """
    pass
2.2. Configuration SchemaThe config dictionary supports standard keys that the Dashboard Builder will eventually populate:title (str): Overrides the default header.height (int): Sets fixed height (crucial for Bento Grid).color_theme (str): Optional override for chart colors.3. The Widget Registry (app/dashboard/registry.py)This module acts as the "Dispatcher". It maps a string ID (stored in JSON layouts) to the actual Python function.from typing import Callable, Dict
from app.dashboard.widgets import kpis, charts, tables

# Type Definition
WidgetRenderer = Callable[[pd.DataFrame, Optional[Dict]], None]

class WidgetRegistry:
    _registry: Dict[str, WidgetRenderer] = {
        # KPIs
        "kpi_total_open": kpis.total_open_issues,
        "kpi_velocity": kpis.weekly_velocity,
        "kpi_stale_count": kpis.stale_issue_count,
        
        # Charts
        "chart_burnup": charts.burnup_velocity,
        "chart_aging_boxplot": charts.aging_distribution,
        "chart_work_distribution": charts.work_type_distribution,
        
        # Tables
        "table_critical_list": tables.critical_issues_list,
        "table_quality_log": tables.data_quality_log
    }

    @classmethod
    def get_renderer(cls, widget_id: str) -> WidgetRenderer:
        renderer = cls._registry.get(widget_id)
        if not renderer:
            raise ValueError(f"Widget ID '{widget_id}' not found in registry.")
        return renderer

    @classmethod
    def list_widgets(cls):
        return list(cls._registry.keys())
4. Implementation Details: Widget Modules4.1. KPI Widgets (widgets/kpis.py)These functions must implement the "Value-First" Design (CSS Styling) defined in previous TSDs.Function: total_open_issues(df, config)Logic: count = len(df[df['state'] == 'opened'])UI: Renders custom HTML/CSS card.Function: stale_issue_count(df, config)Logic: count = df['is_stale'].sum()4.2. Chart Widgets (widgets/charts.py)These functions encapsulate the Plotly logic.Function: burnup_velocity(df, config)Logic: Aggregates created_at vs closed_at.UI: st.plotly_chart(fig, use_container_width=True, height=config.get('height', 400))Constraint: Must respect Dark Mode (transparent background) as per Layer 3 spec.4.3. Table Widgets (widgets/tables.py)These functions encapsulate the st.dataframe and st.dialog logic.Function: critical_issues_list(df, config)Logic: Filter df for high severity/stale issues.UI: Renders the Master-Detail table (Compact list + Modal popup).5. Refactoring Strategy (Migration)We will not break the existing app. We will refactor views/overview.py to become a "Consumer" of the registry.Old overview.py:st.header("Overview")
# ... 50 lines of plotting code ...
st.plotly_chart(fig)
New overview.py:from app.dashboard.registry import WidgetRegistry

st.header("Overview")

# 1. KPIs
c1, c2, c3 = st.columns(3)
with c1: WidgetRegistry.get_renderer("kpi_total_open")(df)
with c2: WidgetRegistry.get_renderer("kpi_velocity")(df)
with c3: WidgetRegistry.get_renderer("kpi_stale_count")(df)

# 2. Charts
WidgetRegistry.get_renderer("chart_burnup")(df, {"height": 500})
6. Definition of Done[ ] Directory app/dashboard/widgets created with __init__.py.[ ] At least 3 widgets (1 KPI, 1 Chart, 1 Table) extracted from current views into the widgets/ modules.[ ] registry.py implements the lookup logic.[ ] One view (e.g., Overview) successfully refactored to use WidgetRegistry.[ ] No regression in UI appearance (Dark Mode and Styles preserved).