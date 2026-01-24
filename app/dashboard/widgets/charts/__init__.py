"""Chart Widgets package.

Individual chart components.
"""

from app.dashboard.widgets.charts.stage_distribution import stage_distribution
from app.dashboard.widgets.charts.aging_boxplot import aging_boxplot
from app.dashboard.widgets.charts.burnup_velocity import burnup_velocity
from app.dashboard.widgets.charts.workload_distribution import workload_distribution
from app.dashboard.widgets.charts.work_type_distribution import work_type_distribution
from app.dashboard.widgets.charts.status_donut import status_donut
from app.dashboard.widgets.charts.quality_gauge import quality_gauge
from app.dashboard.widgets.charts.error_distribution import error_distribution

__all__ = [
    "stage_distribution",
    "aging_boxplot",
    "burnup_velocity",
    "workload_distribution",
    "work_type_distribution",
    "status_donut",
    "quality_gauge",
    "error_distribution",
]
