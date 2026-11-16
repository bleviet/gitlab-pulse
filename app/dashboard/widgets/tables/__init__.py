"""Table Widgets package.

Individual table components.
"""

from app.dashboard.widgets.tables.issue_board import issue_board, issue_card_list
from app.dashboard.widgets.tables.issue_detail_grid import issue_detail_grid

__all__ = [
    "issue_board",
    "issue_card_list",
    "issue_detail_grid",
]
