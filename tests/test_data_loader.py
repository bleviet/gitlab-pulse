"""Tests for dashboard data loading."""

from pathlib import Path

import pandas as pd

from app.dashboard.data_loader import load_valid_issues
from app.dashboard.views.issue_data import lane_priority_counts, priority_labels


def test_load_valid_issues_without_priority_column(tmp_path: Path) -> None:
    """Rules without a priority classification still load and render as Unset."""
    pd.DataFrame(
        {
            "iid": [1, 2, 3],
            "state": ["opened", "opened", "closed"],
            "stage": ["Todo", "Todo", "Done"],
            "created_at": pd.to_datetime(["2025-01-01"] * 3, utc=True),
        }
    ).to_parquet(tmp_path / "issues_valid.parquet")

    df = load_valid_issues(str(tmp_path))

    assert "priority" in df.columns
    assert df["priority"].isna().all()
    assert (priority_labels(df) == "Unset").all()
    assert lane_priority_counts(df) == {
        "Todo": [("Unset", 2)],
        "Done": [("Unset", 1)],
    }
