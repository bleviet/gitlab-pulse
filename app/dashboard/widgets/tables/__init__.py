"""Table Widgets package.

Individual table components.
"""

from app.dashboard.widgets.tables.issue_detail_grid import issue_detail_grid
from app.dashboard.widgets.tables.stale_issues_list import stale_issues_list
from app.dashboard.widgets.tables.quality_action_table import quality_action_table
from app.dashboard.widgets.tables.capacity_grid import capacity_grid

__all__ = [
    "issue_detail_grid",
    "stale_issues_list",
    "quality_action_table",
    "capacity_grid",
]
