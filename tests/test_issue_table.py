"""The issue table shows one page and computes quality hints only for it."""

from typing import Any

import pandas as pd
import pytest

from app.dashboard.views import issue_table
from app.dashboard.views.issue_pages import PageWindow


def _issues() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "iid": [1, 2, 3, 4],
            "title": ["a", "b", "c", "d"],
            "web_url": [f"https://x/{n}" for n in range(1, 5)],
            "stage": ["Backlog", "Implementation", "Implementation", "Testing"],
            "state": ["opened"] * 4,
            "priority": ["Medium", "Medium", "High", "Medium"],
            "priority_rank": [2, 2, 1, 2],
            "days_in_stage": [1, 2, 3, 4],
            "assignee": [None] * 4,
            "milestone": [None] * 4,
            "labels": [["type::bug"]] * 4,
            "context": [None] * 4,
        }
    )


def test_prepare_issue_rows_leaves_the_hints_to_the_page() -> None:
    rows = issue_table.prepare_issue_rows(_issues())

    assert "quality_hints" not in rows.columns


def test_table_computes_hints_only_for_the_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []
    original = issue_table._issue_quality_hints_text

    def counting(row: pd.Series) -> str:
        calls.append(1)
        return original(row)

    shown: dict[str, pd.DataFrame] = {}

    def grid(styler: Any, *_a: Any, **_k: Any) -> None:
        shown["frame"] = styler.data

    monkeypatch.setattr(issue_table, "load_labels", lambda: {})
    monkeypatch.setattr(issue_table.tables, "issue_detail_grid", grid)
    monkeypatch.setattr(issue_table, "_issue_quality_hints_text", counting)

    rows = issue_table.prepare_issue_rows(_issues().assign(context=[[]] * 4))
    issue_table.render_issue_table(rows, {}, PageWindow(0, 2))

    frame = shown["frame"]
    assert len(calls) == 2
    assert len(frame) == 2
    assert frame["quality_hints"].tolist() == [
        "Unassigned owner | Missing milestone"
    ] * 2
    assert frame["quality_hints"].tolist() == [
        original(row) for _, row in rows.iloc[0:2].iterrows()
    ]
