"""Rows (table) or cards per lane (board) shown for each page size."""

import importlib

pages = importlib.import_module("app.dashboard.views.issue_pages")


def test_a_page_of_rows() -> None:
    assert pages.page_bounds(408, "10", 0) == (0, 10, 0)
    assert pages.page_bounds(408, "20", 1) == (20, 40, 1)
    assert pages.page_bounds(408, "30", 13) == (390, 408, 13)


def test_page_is_clamped_when_the_rows_shrink() -> None:
    """A filter can leave fewer rows than the current page needs."""
    assert pages.page_bounds(25, "10", 5) == (20, 25, 2)
    assert pages.page_bounds(0, "10", 2) == (0, 0, 0)
    assert pages.page_bounds(8, "10", -1) == (0, 8, 0)
