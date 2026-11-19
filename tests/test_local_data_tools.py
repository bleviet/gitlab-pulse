"""Tests for local synthetic data tooling."""

from pathlib import Path

import numpy as np
import pandas as pd

from app.dashboard.utils import (
    SIGNAL_MISSING_MILESTONE,
    SIGNAL_MIXED_CLASSIFICATION,
    SIGNAL_UNASSIGNED_OWNER,
    compute_issue_signals_and_hints,
    is_local_issue_url,
    mixed_classification_hints,
    normalize_assignee_labels,
    normalize_issue_labels,
)
from tools.local_data_manager import delete_local_projects, discover_local_projects
from tools.seeder import build_local_issue_url, generate_issues, seed_data


def test_generate_issues_respects_max_team_members() -> None:
    """Seeder should bound unique assignees by the configured team size."""
    df = generate_issues(
        count=120,
        project_ids=[101],
        seed=42,
        assignment_rate=1.0,
        max_team_members=5,
    )

    unique_assignees = set(df["assignee"].dropna().tolist())

    assert len(unique_assignees) == 5
    assert is_local_issue_url(df["web_url"].iloc[0])


def test_generate_issues_allows_unassigned_issues() -> None:
    """Seeder should honor assignment_rate=0 for no assigned tickets."""
    df = generate_issues(
        count=30,
        project_ids=[101],
        seed=7,
        assignment_rate=0.0,
        max_team_members=3,
    )

    assert df["assignee"].isna().all()


def test_generate_issues_adds_example_activity_notes() -> None:
    """Seeder should attach sample activity notes to generated issues."""
    df = generate_issues(
        count=10,
        project_ids=[101],
        seed=21,
        assignment_rate=1.0,
        max_team_members=3,
    )

    notes = df["notes"].iloc[0]

    assert isinstance(notes, list)
    assert notes
    assert {"author_name", "author_username", "body", "created_at", "system"} <= set(notes[0])


def test_generate_issues_populates_grouped_child_tasks_within_project() -> None:
    """Seeder should attach child tasks to parent ISSUE items in the same project."""
    df = generate_issues(
        count=200,
        project_ids=[101, 102],
        seed=42,
    )

    by_id = df.set_index("id")
    parents_with_children = df[df["child_ids"].apply(lambda ids: len(ids) >= 2)]
    assert len(parents_with_children) > 0
    assert (parents_with_children["work_item_type"] == "ISSUE").all()

    tasks_with_parent = df[df["parent_id"].notna()]
    assert len(tasks_with_parent) > 0
    for _, task in tasks_with_parent.iterrows():
        parent_id = int(task["parent_id"])
        assert parent_id in by_id.index
        parent = by_id.loc[parent_id]
        assert parent["project_id"] == task["project_id"]
        assert parent["work_item_type"] == "ISSUE"
        assert int(task["iid"]) in parent["child_ids"]



def test_normalize_assignee_labels_maps_missing_values_to_unassigned() -> None:
    """Dashboard assignee labels should treat missing values consistently."""
    labels = normalize_assignee_labels(
        pd.Series([None, "", "  ", "nan", "<NA>", "None", "alice"])
    )

    assert labels.tolist() == [
        "Unassigned",
        "Unassigned",
        "Unassigned",
        "Unassigned",
        "Unassigned",
        "Unassigned",
        "alice",
    ]


def test_build_local_issue_url_uses_dashboard_query_params() -> None:
    """Synthetic issue URLs should deep-link back into the local dashboard."""
    url = build_local_issue_url(
        project_id=101,
        issue_iid=7,
        dashboard_url_base="http://localhost:8501",
    )

    assert url == (
        "http://localhost:8501/"
        "?issue_source=local&issue_project_id=101&issue_iid=7"
    )


def test_normalize_issue_labels_splits_numpy_style_label_string() -> None:
    """Issue label chips should split numpy-style string arrays into values."""
    raw = (
        "['type::bug' 'severity::critical' 'priority::1' "
        "'cve' 'project::B' 'workflow::architecture']"
    )

    assert normalize_issue_labels(raw) == [
        "type::bug",
        "severity::critical",
        "priority::1",
        "cve",
        "project::B",
        "workflow::architecture",
    ]


def test_normalize_issue_labels_preserves_real_label_lists() -> None:
    """Issue label chips should keep already-materialized label lists intact."""
    assert normalize_issue_labels(["type::bug", "severity::critical", ""]) == [
        "type::bug",
        "severity::critical",
    ]


def test_normalize_issue_labels_treats_numpy_arrays_like_lists() -> None:
    """Parquet list columns arrive as numpy arrays and must match plain lists."""
    cases = [
        ["type::bug", "severity::critical", ""],
        ["type::bug"],
        [],
    ]
    for labels in cases:
        array = np.array(labels, dtype=object)
        assert normalize_issue_labels(array) == normalize_issue_labels(labels)
    assert normalize_issue_labels(np.array(["type::bug"], dtype=object)) == ["type::bug"]
    assert normalize_issue_labels(np.array([], dtype=object)) == []


def test_mixed_classification_hints_detects_numpy_arrays_and_conflicts() -> None:
    """Mixed classification hints should explain conflicting labels."""
    labels = normalize_issue_labels(np.array(["type::bug", "type::feature", "severity::high"], dtype=object))
    assert mixed_classification_hints(labels) == ["Mixed type labels: type::bug + type::feature"]
    assert mixed_classification_hints(["type::bug", "severity::high"]) == []


def test_compute_issue_signals_and_hints_only_flags_opened_issues() -> None:
    """Quality signals and hints apply to opened issues and skip closed ones."""
    signals, hints = compute_issue_signals_and_hints(
        state="opened",
        labels=["type::bug", "type::feature"],
        assignee="Unassigned",
        milestone=None,
    )
    assert signals == [
        SIGNAL_MIXED_CLASSIFICATION,
        SIGNAL_UNASSIGNED_OWNER,
        SIGNAL_MISSING_MILESTONE,
    ]
    assert hints == [
        "Mixed type labels: type::bug + type::feature",
        "Unassigned owner",
        "Missing milestone",
    ]

    closed_signals, closed_hints = compute_issue_signals_and_hints(
        state="closed",
        labels=["type::bug", "type::feature"],
        assignee="Unassigned",
        milestone=None,
    )
    assert closed_signals == []
    assert closed_hints == []


def test_discover_local_projects_reads_seeded_summaries(tmp_path: Path) -> None:
    """Local data manager should detect and summarize seeded projects."""
    seed_data(
        count=60,
        project_ids=[201, 202],
        output_path=tmp_path / "processed",
        seed=123,
        assignment_rate=1.0,
        max_team_members=4,
    )

    projects = discover_local_projects(tmp_path)

    assert [project.project_id for project in projects] == [201, 202]
    assert all(project.issue_count > 0 for project in projects)
    assert all(project.unique_assignees <= 4 for project in projects)


def test_delete_local_projects_removes_related_files(tmp_path: Path) -> None:
    """Deleting a project should remove matching processed files."""
    processed_path = tmp_path / "processed"
    processed_path.mkdir(parents=True, exist_ok=True)

    sample_df = pd.DataFrame(
        [
            {
                "id": 1,
                "iid": 1,
                "project_id": 201,
                "title": "Issue",
                "state": "opened",
                "created_at": pd.Timestamp("2024-01-01", tz="UTC"),
                "updated_at": pd.Timestamp("2024-01-02", tz="UTC"),
                "closed_at": None,
                "labels": [["type::task"]],
                "work_item_type": "ISSUE",
                "parent_id": None,
                "child_ids": [[]],
                "web_url": "https://example.com",
                "assignee": "alice",
                "milestone": None,
                "milestone_id": None,
                "milestone_due_date": None,
                "milestone_start_date": None,
            }
        ]
    )
    sample_df.to_parquet(processed_path / "issues_201.parquet", engine="pyarrow", compression="snappy")
    sample_df.to_parquet(processed_path / "milestones_201.parquet", engine="pyarrow", compression="snappy")
    sample_df.to_parquet(processed_path / "labels_201.parquet", engine="pyarrow", compression="snappy")

    removed = delete_local_projects([201], data_path=tmp_path)

    assert len(removed) == 3
    assert not (processed_path / "issues_201.parquet").exists()
    assert not (processed_path / "milestones_201.parquet").exists()
    assert not (processed_path / "labels_201.parquet").exists()
