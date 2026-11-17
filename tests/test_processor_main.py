"""Tests for the Layer 2 processor entry point."""

from pathlib import Path

import pandas as pd

from app.processor.main import Processor


def _stale_valid_file(tmp_path: Path) -> Path:
    analytics = tmp_path / "analytics"
    analytics.mkdir(parents=True, exist_ok=True)
    stale = analytics / "issues_valid.parquet"
    pd.DataFrame({"id": [1, 2]}).to_parquet(stale)
    return stale


def test_process_all_overwrites_stale_valid_file_when_no_issue_is_valid(
    tmp_path: Path,
) -> None:
    """A processed file with no rows must clear a stale issues_valid.parquet."""
    stale = _stale_valid_file(tmp_path)
    processed = tmp_path / "processed"
    processed.mkdir()
    pd.DataFrame(
        {"id": pd.Series([], dtype="int64")}
    ).to_parquet(processed / "issues_7.parquet")

    result = Processor(
        data_path=tmp_path, rules_path=Path("app/config/rules")
    ).process_all()

    assert result["valid"] == 0
    assert pd.read_parquet(stale).empty


def test_process_all_overwrites_stale_valid_file_without_processed_files(
    tmp_path: Path,
) -> None:
    """No processed files must still clear a stale issues_valid.parquet."""
    stale = _stale_valid_file(tmp_path)

    result = Processor(
        data_path=tmp_path, rules_path=Path("app/config/rules")
    ).process_all()

    assert result == {"valid": 0, "quality": 0}
    assert pd.read_parquet(stale).empty
