"""Widget package for Layer 3 Dashboard.

Provides reusable, standalone widget components that can be composed
into views or rendered by the Dashboard Builder grid engine.

Structure:
    widgets/
    ├── kpis/           # KPI metric cards
    ├── charts/         # Plotly charts
    └── tables/         # DataFrames and grids
"""

from app.dashboard.widgets import kpis, charts, tables, features

__all__ = ["kpis", "charts", "tables"]
