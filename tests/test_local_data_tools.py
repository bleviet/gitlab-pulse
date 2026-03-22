"""Tests for local synthetic data tooling."""

from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from app.ai.models import IssueConversation
from app.dashboard.utils import normalize_assignee_labels
from app.dashboard.views.overview import (
    _build_issue_ai_context_row,
    _build_issue_search_mask,
    _build_local_issue_details,
    _build_overview_quality_signal_df,
    _dialog_meta_item_html,
    _has_multiple_classification_labels,
    _is_local_issue_url,
    _issue_dialog_scroll_script,
    _issue_quality_hints,
    _mixed_classification_hints,
    _normalize_issue_labels,
    _normalize_issue_search_text,
    _priority_cell_style,
    _priority_color_key,
    _selection_mask_for_quality_signal,
    _selection_mask_for_value,
)
from app.dashboard.widgets.features.ai_assistant import (
    _conversation_is_stale,
    _format_issue_labels,
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
            "notes": np.array(
                [
                    {
                        "author_name": "Alex Rivera",
                        "author_username": "arivera",
                        "body": "Checked the latest repro.",
                        "created_at": "2024-01-02T10:00:00Z",
                        "system": False,
                    }
                ],
                dtype=object,
            ),
        }
    )

    details = _build_local_issue_details(row)

    assert details["title"] == "Seeded issue"
    assert details["description"] == "Local description"
    assert details["web_url"].endswith("issue_iid=3")
    assert len(details["notes"]) == 1
    assert details["notes"][0]["author_username"] == "arivera"


def test_build_issue_ai_context_row_prefers_loaded_details() -> None:
    """AI context rows should use the loaded issue details inside the dialog."""
    row = pd.Series(
        {
            "id": 42,
            "title": "Table title",
            "description": "",
            "web_url": "https://gitlab.example.com/issues/42",
        }
    )
    issue_details = {
        "title": "Loaded title",
        "description": "Loaded description",
        "web_url": "https://gitlab.example.com/group/project/-/issues/42",
        "notes": [],
    }

    ai_row = _build_issue_ai_context_row(row, issue_details)

    assert ai_row["title"] == "Loaded title"
    assert ai_row["description"] == "Loaded description"
    assert ai_row["web_url"] == "https://gitlab.example.com/group/project/-/issues/42"


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


def test_dialog_meta_item_html_adds_separator_and_escapes_content() -> None:
    """Dialog metadata sections should render dividers with escaped text."""
    html_markup = _dialog_meta_item_html(
        label="Stage <Current>",
        value="Review & QA",
        divider_color="rgba(255,255,255,0.14)",
        label_color="rgba(255,255,255,0.72)",
        value_color="#d4deee",
    )

    assert "border-bottom:1px solid rgba(255,255,255,0.14)" in html_markup
    assert "Stage &lt;Current&gt;" in html_markup
    assert "Review &amp; QA" in html_markup


def test_issue_dialog_scroll_script_targets_dialog_top_marker() -> None:
    """Issue dialog scroll helper should target the top marker in the modal."""
    script = _issue_dialog_scroll_script()

    assert 'const markerId = "issue-details-dialog-top"' in script
    assert "scrollIntoView" in script
    assert "node.scrollTop = 0" in script


def test_conversation_is_stale_detects_newer_issue_updates() -> None:
    """AI status should mark summaries stale when the source issue changed."""
    row = pd.Series({"updated_at": "2024-01-03T12:00:00Z"})
    conversation = IssueConversation(
        issue_id=1,
        project_id=101,
        ref_issue_updated_at=datetime(2024, 1, 2, 12, 0, tzinfo=UTC),
        summary_short="Summary",
    )

    assert _conversation_is_stale(row, conversation) is True


def test_format_issue_labels_handles_iterables_and_empty_values() -> None:
    """AI metadata should render labels predictably for display."""
    assert _format_issue_labels(["type::bug", "", "priority::1"]) == (
        "`type::bug` `priority::1`"
    )
    assert _format_issue_labels(None) == "_No labels_"


def test_has_multiple_classification_labels_detects_duplicate_type_family() -> None:
    """Overview quality signals should flag issues with conflicting classification labels."""
    assert _has_multiple_classification_labels(["type::bug", "type::feature"]) is True
    assert _has_multiple_classification_labels(["type::bug", "severity::high"]) is False


def test_mixed_classification_hints_describe_conflicting_labels() -> None:
    """Mixed classification hints should explain exactly which labels conflict."""
    hints = _mixed_classification_hints(["type::bug", "type::feature", "severity::high"])

    assert hints == ["Mixed type labels: type::bug + type::feature"]


def test_issue_quality_hints_include_reason_details() -> None:
    """Issue quality hints should surface the specific mixed-classification reason."""
    row = pd.Series(
        {
            "labels": ["type::bug", "type::feature"],
            "assignee": None,
            "milestone": None,
        }
    )

    assert _issue_quality_hints(row) == [
        "Mixed type labels: type::bug + type::feature",
        "Unassigned owner",
        "Missing milestone",
    ]


def test_build_overview_quality_signal_df_collects_three_focus_signals() -> None:
    """Overview quality signals should cover mixed classification, owner, and milestone gaps."""
    df = pd.DataFrame(
        [
            {
                "id": 1,
                "labels": ["type::bug", "type::feature"],
                "assignee": "alex",
                "milestone": "Release 24",
            },
            {
                "id": 2,
                "labels": ["type::task"],
                "assignee": None,
                "milestone": "Release 24",
            },
            {
                "id": 3,
                "labels": ["type::feature"],
                "assignee": "sam",
                "milestone": None,
            },
            {
                "id": 4,
                "labels": ["type::bug"],
                "assignee": None,
                "milestone": None,
            },
        ]
    )

    signal_df = _build_overview_quality_signal_df(df)
    grouped_signals = signal_df.groupby("error_code")["id"].apply(list).to_dict()

    assert grouped_signals == {
        "MIXED_CLASSIFICATION": [1],
        "MISSING_MILESTONE": [3, 4],
        "UNASSIGNED_OWNER": [2, 4],
    }


def test_selection_mask_for_quality_signal_matches_filtered_issue_rows() -> None:
    """Clicking an Overview quality-signal bar should filter the matching issues."""
    df = pd.DataFrame(
        [
            {
                "id": 1,
                "labels": ["type::bug", "type::feature"],
                "assignee": "alex",
                "milestone": "Release 24",
            },
            {
                "id": 2,
                "labels": ["type::task"],
                "assignee": None,
                "milestone": "Release 24",
            },
            {
                "id": 3,
                "labels": ["type::feature"],
                "assignee": "sam",
                "milestone": None,
            },
        ]
    )

    mixed_mask = _selection_mask_for_quality_signal(df, "MIXED_CLASSIFICATION")
    unassigned_mask = _selection_mask_for_quality_signal(df, "UNASSIGNED_OWNER")
    milestone_mask = _selection_mask_for_quality_signal(df, "MISSING_MILESTONE")

    assert mixed_mask.tolist() == [True, False, False]
    assert unassigned_mask.tolist() == [False, True, False]
    assert milestone_mask.tolist() == [False, False, True]


def test_build_issue_search_mask_matches_terms_across_multiple_columns() -> None:
    """Grid search should match assignee, context, milestone, and severity cells."""
    df = pd.DataFrame(
        [
            {
                "iid": 11,
                "title": "Stabilize auth redirect",
                "stage": "Review",
                "days_in_stage": 4,
                "severity": "high",
                "context": "customer",
                "milestone": "v1.2",
                "assignee": "alex",
            },
            {
                "iid": 12,
                "title": "Refine local search indexing",
                "stage": "In Progress",
                "days_in_stage": 9,
                "severity": "medium",
                "context": "platform",
                "milestone": "v1.3",
                "assignee": "sam",
            },
        ]
    )

    mask = _build_issue_search_mask(df, "alex customer v1.2 high")

    assert mask.tolist() == [True, False]


def test_build_issue_search_mask_supports_fuzzy_matches() -> None:
    """Grid search should tolerate minor typos against table cell values."""
    df = pd.DataFrame(
        [
            {
                "iid": 21,
                "title": "Improve milestone summary",
                "stage": "Testing",
                "days_in_stage": 2,
                "severity": "critical",
                "context": "security",
                "milestone": "Release 24",
                "assignee": "taylor",
            }
        ]
    )

    mask = _build_issue_search_mask(df, "critcal")

    assert mask.tolist() == [True]


def test_normalize_issue_search_text_flattens_collection_values() -> None:
    """Grid search normalization should flatten lists and remove label separators."""
    normalized = _normalize_issue_search_text(["priority::1", "workflow::review"])

    assert normalized == "priority 1 workflow review"


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
