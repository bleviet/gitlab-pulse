"""Widget Registry for Layer 3 Dashboard.

Central dispatcher that maps string IDs to widget render functions.
Used by the Dashboard Builder grid engine to instantiate widgets.
"""

from typing import Any, Callable, Optional

import pandas as pd

from app.dashboard.widgets.kpis import (
    flow_metrics, stats_kpis, release_metrics, stale_count, quality_score
)
from app.dashboard.widgets.charts import (
    stage_distribution, aging_boxplot, burnup_velocity,
    workload_distribution, work_type_distribution, status_donut,
    quality_gauge, error_distribution
)
from app.dashboard.widgets.tables import (
    issue_detail_grid, stale_issues_list, quality_action_table, capacity_grid
)

# Type alias for widget render functions
WidgetRenderer = Callable[[pd.DataFrame, Optional[dict[str, Any]]], None]


class WidgetRegistry:
    """Registry of available widget components."""

    _registry: dict[str, WidgetRenderer] = {
        # KPIs
        "kpi_flow_metrics": flow_metrics,
        "kpi_stats": stats_kpis,
        "kpi_stale_count": stale_count,
        "kpi_quality_score": quality_score,

        # Charts
        "chart_stage_distribution": stage_distribution,
        "chart_aging_boxplot": aging_boxplot,
        "chart_burnup_velocity": burnup_velocity,
        "chart_workload_distribution": workload_distribution,
        "chart_work_type_distribution": work_type_distribution,
        "chart_status_donut": status_donut,
        "chart_quality_gauge": quality_gauge,
        "chart_error_distribution": error_distribution,

        # Tables
        "table_issue_detail_grid": issue_detail_grid,
        "table_stale_issues_list": stale_issues_list,
        "table_quality_action": quality_action_table,
        "table_capacity_grid": capacity_grid,
    }

    @classmethod
    def get_renderer(cls, widget_id: str) -> WidgetRenderer:
        """Get widget renderer function by ID.

        Args:
            widget_id: Unique identifier for the widget

        Returns:
            Widget render function

        Raises:
            ValueError: If widget_id not found in registry
        """
        renderer = cls._registry.get(widget_id)
        if not renderer:
            raise ValueError(f"Widget ID '{widget_id}' not found in registry.")
        return renderer

    @classmethod
    def list_widgets(cls) -> list[str]:
        """List all registered widget IDs.

        Returns:
            List of widget ID strings
        """
        return list(cls._registry.keys())

    @classmethod
    def get_widget_info(cls) -> dict[str, dict[str, str]]:
        """Get metadata about all registered widgets.

        Returns:
            Dict mapping widget_id to info dict with category and name
        """
        info = {}
        for widget_id in cls._registry:
            parts = widget_id.split("_", 1)
            category = parts[0] if parts else "other"
            name = parts[1].replace("_", " ").title() if len(parts) > 1 else widget_id
            info[widget_id] = {"category": category, "name": name}
        return info
