"""KPI Widgets package.

Individual KPI metric card components.
"""

from app.dashboard.widgets.kpis.flow_metrics import flow_metrics
from app.dashboard.widgets.kpis.stats_kpis import stats_kpis
from app.dashboard.widgets.kpis.release_metrics import release_metrics
from app.dashboard.widgets.kpis.stale_count import stale_count
from app.dashboard.widgets.kpis.quality_score import quality_score
from app.dashboard.widgets.kpis.daily_summary_kpi import daily_summary_kpi

__all__ = [
    "flow_metrics",
    "stats_kpis",
    "release_metrics",
    "stale_count",
    "quality_score",
    "daily_summary_kpi",
]
