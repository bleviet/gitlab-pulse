"""KPI Widgets package.

Individual KPI metric card components.
"""

from app.dashboard.widgets.kpis.flow_metrics import flow_metrics
from app.dashboard.widgets.kpis.stale_count import stale_count
from app.dashboard.widgets.kpis.quality_score import quality_score

__all__ = [
    "flow_metrics",
    "stale_count",
    "quality_score",
]
