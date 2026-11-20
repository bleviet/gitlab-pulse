"""Tests for the Layer 2 processor entry point."""

from pathlib import Path

import pandas as pd

from app.processor.main import Processor, process_issues
from app.processor.rule_loader import RuleLoader, load_rule_file
from app.processor.rule_store import dump_rule


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


def _write_issues(processed: Path, project_id: int) -> pd.DataFrame:
    now = pd.Timestamp.now(tz="UTC")
    rows = [
        (1, "opened", ["type::bug", "workflow::review", "priority::1", "project::A"]),
        (2, "closed", ["type::feature", "project::A", "project::B"]),
        (3, "opened", []),
        (4, "opened", ["type::bug", "type::feature", "project::B"]),
    ]
    df = pd.DataFrame(
        {
            "id": [r[0] for r in rows],
            "iid": [r[0] for r in rows],
            "project_id": project_id,
            "title": [f"Issue {r[0]}" for r in rows],
            "state": [r[1] for r in rows],
            "created_at": now - pd.Timedelta(days=60),
            "updated_at": now - pd.Timedelta(days=45),
            "closed_at": [pd.NaT, now - pd.Timedelta(days=10), pd.NaT, pd.NaT],
            "labels": [r[2] for r in rows],
            "work_item_type": "ISSUE",
            "parent_id": float("nan"),
            "assignee": "someone",
        }
    )
    processed.mkdir(parents=True, exist_ok=True)
    df.to_parquet(processed / f"issues_{project_id}.parquet")
    return df


def _rules_dir(tmp_path: Path, require_assignment: bool) -> Path:
    rule = load_rule_file(Path("app/config/rules/default.yaml"))
    rule.contexts.require_assignment = require_assignment
    rules_dir = tmp_path / "rules"
    rules_dir.mkdir()
    rules_dir.joinpath("default.yaml").write_text(dump_rule(rule), encoding="utf-8")
    return rules_dir


def test_process_project_matches_process_issues_by_default(tmp_path: Path) -> None:
    df = _write_issues(tmp_path / "processed", 7)
    rules_dir = _rules_dir(tmp_path, require_assignment=False)
    processor = Processor(data_path=tmp_path, rules_path=rules_dir)

    valid, quality = processor.process_project(7)

    rule = RuleLoader(rules_dir).get_rule(7)
    assert rule is not None
    expected_valid, expected_quality = process_issues(df, rule)
    pd.testing.assert_frame_equal(valid, expected_valid)
    pd.testing.assert_frame_equal(quality, expected_quality)
    by_id = valid.drop_duplicates("id").set_index("id")
    assert by_id.loc[1, "issue_type"] == "Bug"
    assert by_id.loc[1, "stage"] == "Review"
    assert by_id.loc[2, "stage"] == "Done"
    assert by_id.loc[3, "stage"] == "Backlog"
    assert len(valid[valid["id"] == 2]) == 2
    assert set(valid.loc[valid["id"] == 2, "context_group"]) == {"ProjectA", "ProjectB"}
    assert valid.loc[valid["id"] == 3, "context_group"].isna().all()
    assert list(quality["error_code"]) == ["CONFLICTING_LABELS"]
    assert list(quality["id"]) == [4]


def test_process_project_matches_process_issues_with_required_assignment(
    tmp_path: Path,
) -> None:
    df = _write_issues(tmp_path / "processed", 7)
    rules_dir = _rules_dir(tmp_path, require_assignment=True)
    processor = Processor(data_path=tmp_path, rules_path=rules_dir)

    valid, quality = processor.process_project(7)

    rule = RuleLoader(rules_dir).get_rule(7)
    assert rule is not None
    expected_valid, expected_quality = process_issues(df, rule)
    pd.testing.assert_frame_equal(valid, expected_valid)
    pd.testing.assert_frame_equal(quality, expected_quality)
    assert (quality.loc[quality["id"] == 3, "error_code"] == "MISSING_CONTEXT").all()
    assert valid.loc[valid["id"] == 3, "context_group"].isna().all()
    assert 3 in set(valid["id"])
