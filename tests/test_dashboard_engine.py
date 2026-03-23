"""Tests for the shared dashboard grid engine helpers."""

import pytest

from app.dashboard.engine import (
    StreamlitGridCell,
    _build_streamlit_row_widths,
    _group_layout_items_by_row,
)


def test_build_streamlit_row_widths_adds_trailing_spacer() -> None:
    """Rows that do not fill the full grid should receive a spacer column."""
    widths = _build_streamlit_row_widths(
        (
            StreamlitGridCell(key="left", span=3, render=lambda: None),
            StreamlitGridCell(key="middle", span=3, render=lambda: None),
            StreamlitGridCell(key="right", span=4, render=lambda: None),
        )
    )

    assert widths == [3, 3, 4, 2]


def test_build_streamlit_row_widths_rejects_overflow() -> None:
    """Rows should fail fast when spans exceed the configured grid width."""
    with pytest.raises(ValueError, match="Grid row uses 13 columns"):
        _build_streamlit_row_widths(
            (
                StreamlitGridCell(key="left", span=7, render=lambda: None),
                StreamlitGridCell(key="right", span=6, render=lambda: None),
            )
        )


def test_group_layout_items_by_row_sorts_by_y_then_x() -> None:
    """Persisted layout items should be grouped into sorted grid rows."""
    grouped = _group_layout_items_by_row(
        [
            {"i": "b", "x": 6, "y": 1, "w": 6, "h": 2, "type": "chart_b"},
            {"i": "a", "x": 0, "y": 0, "w": 3, "h": 2, "type": "chart_a"},
            {"i": "c", "x": 3, "y": 0, "w": 9, "h": 2, "type": "chart_c"},
        ]
    )

    assert [[item["i"] for item in row] for row in grouped] == [["a", "c"], ["b"]]
