"""Tests for local synthetic data tooling."""

from pathlib import Path

import pandas as pd

from app.dashboard.utils import normalize_assignee_labels
from app.dashboard.views.overview import (
    _build_local_issue_details,
    _is_local_issue_url,
    _normalize_issue_labels,
    _priority_cell_style,
    _priority_color_key,
    _selection_mask_for_value,
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
    assert _is_local_issue_url(df["web_url"].iloc[0])


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


def test_selection_mask_matches_unassigned_assignee_rows() -> None:
    """Clicking the Unassigned assignee bar should match null and blank assignees."""
    df = pd.DataFrame(
        [
            {"id": 1, "assignee": None, "stage": "Todo", "severity": None, "state": "opened"},
            {"id": 2, "assignee": "", "stage": "Doing", "severity": "medium", "state": "opened"},
            {"id": 3, "assignee": "alice", "stage": "Done", "severity": "high", "state": "closed"},
        ]
    )

    mask = _selection_mask_for_value(df, "Unassigned")

    assert mask.tolist() == [True, True, False]


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


def test_build_local_issue_details_uses_seeded_row_data() -> None:
    """Local issue detail rendering should come from the parquet row."""
    row = pd.Series(
        {
            "title": "Seeded issue",
            "description": "Local description",
            "web_url": build_local_issue_url(101, 3),
        }
    )

    details = _build_local_issue_details(row)

    assert details["title"] == "Seeded issue"
    assert details["description"] == "Local description"
    assert details["web_url"].endswith("issue_iid=3")
    assert details["notes"] == []


def test_normalize_issue_labels_splits_numpy_style_label_string() -> None:
    """Issue label chips should split numpy-style string arrays into values."""
    raw = (
        "['type::bug' 'severity::critical' 'priority::1' "
        "'cve' 'project::B' 'workflow::architecture']"
    )

    assert _normalize_issue_labels(raw) == [
        "type::bug",
        "severity::critical",
        "priority::1",
        "cve",
        "project::B",
        "workflow::architecture",
    ]


def test_normalize_issue_labels_preserves_real_label_lists() -> None:
    """Issue label chips should keep already-materialized label lists intact."""
    assert _normalize_issue_labels(["type::bug", "severity::critical", ""]) == [
        "type::bug",
        "severity::critical",
    ]


def test_priority_color_key_normalizes_severity_and_priority_labels() -> None:
    """Priority cell styling should accept both severity and priority values."""
    assert _priority_color_key("High") == "high"
    assert _priority_color_key("P2") == "p2"
    assert _priority_color_key("priority::3") == "p3"
    assert _priority_color_key(None) == "unset"


def test_priority_cell_style_uses_palette_defaults_for_known_values() -> None:
    """Priority cell styling should resolve to semantic palette colors."""
    style = _priority_cell_style("High")

    assert style is not None
    assert "background-color:" in style
    assert "font-weight: 700;" in style


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
