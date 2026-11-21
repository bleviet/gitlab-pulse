"""Unit tests for the Layer 3 DashboardService and palette resolution."""

import json
from pathlib import Path

import pandas as pd

from app.dashboard.palettes import find_default_rule, resolve_palettes
from app.dashboard.service import DashboardService, _extract_stages
from app.processor.rule_loader import DomainRule, StageConfig, WorkflowConfig


def _write_fixture_data(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    analytics_dir = tmp_path / "analytics"
    processed_dir = tmp_path / "processed"
    state_file = tmp_path / "state" / "sync_state.json"
    rules_dir = tmp_path / "rules"
    analytics_dir.mkdir(parents=True)
    processed_dir.mkdir(parents=True)
    state_file.parent.mkdir(parents=True)
    rules_dir.mkdir(parents=True)

    rules_dir.joinpath("default.yaml").write_text(
        """
project_ids: []
team: "default"
classification:
  priority:
    P1:
      labels: ["priority::1"]
    P2:
      labels: ["priority::2"]
workflow:
  stages:
    - name: "Review"
      labels: ["workflow::review"]
      type: "waiting"
      description: "Peer review"
colors:
  dark:
    p1: "#ff0055"
  light:
    p1: "#cc0044"
""".strip(),
        encoding="utf-8",
    )

    state_file.write_text(
        json.dumps({"projects": {"101": {"last_sync_at": "2026-11-01T12:30:00Z"}}}),
        encoding="utf-8",
    )

    labels_df = pd.DataFrame(
        [{"name": "project::A", "color": "#4facfe", "text_color": "#050811"}]
    )
    labels_df.to_parquet(processed_dir / "labels_101.parquet", engine="pyarrow")

    issues_df = pd.DataFrame(
        [
            {
                "id": 1,
                "iid": 10,
                "project_id": 101,
                "title": "Exploded issue",
                "state": "opened",
                "created_at": pd.Timestamp("2026-11-01T10:00:00Z"),
                "updated_at": pd.Timestamp("2026-11-02T10:00:00Z"),
                "closed_at": pd.NaT,
                "labels": ["type::bug", "type::feature", "project::A"],
                "work_item_type": "ISSUE",
                "parent_id": float("nan"),
                "child_ids": [11],
                "web_url": "https://gitlab.example/issues/10",
                "assignee": None,
                "milestone": None,
                "milestone_id": float("nan"),
                "milestone_due_date": pd.NaT,
                "milestone_start_date": pd.NaT,
                "age_days": 5,
                "cycle_time": float("nan"),
                "is_stale": False,
                "issue_type": "Bug",
                "impact": "High",
                "priority": None,
                "priority_rank": float("nan"),
                "team": "default",
                "stage": "Review",
                "stage_type": "waiting",
                "stage_order": 3,
                "days_in_stage": 2,
                "context": "project::A",
            },
            {
                "id": 1,
                "iid": 10,
                "project_id": 101,
                "title": "Exploded issue",
                "state": "opened",
                "created_at": pd.Timestamp("2026-11-01T10:00:00Z"),
                "updated_at": pd.Timestamp("2026-11-02T10:00:00Z"),
                "closed_at": pd.NaT,
                "labels": ["type::bug", "type::feature", "project::B"],
                "work_item_type": "ISSUE",
                "parent_id": float("nan"),
                "child_ids": [11],
                "web_url": "https://gitlab.example/issues/10",
                "assignee": None,
                "milestone": None,
                "milestone_id": float("nan"),
                "milestone_due_date": pd.NaT,
                "milestone_start_date": pd.NaT,
                "age_days": 5,
                "cycle_time": float("nan"),
                "is_stale": False,
                "issue_type": "Bug",
                "impact": "High",
                "priority": None,
                "priority_rank": float("nan"),
                "team": "default",
                "stage": "Review",
                "stage_type": "waiting",
                "stage_order": 3,
                "days_in_stage": 2,
                "context": "project::B",
            },
            {
                "id": 2,
                "iid": 11,
                "project_id": 101,
                "title": "Closed issue",
                "state": "closed",
                "created_at": pd.Timestamp("2026-10-15T08:00:00Z"),
                "updated_at": pd.Timestamp("2026-10-20T09:00:00Z"),
                "closed_at": pd.Timestamp("2026-10-20T09:00:00Z"),
                "labels": ["priority::1"],
                "work_item_type": "TASK",
                "parent_id": 10.0,
                "child_ids": [],
                "web_url": "https://gitlab.example/issues/11",
                "assignee": "alice",
                "milestone": "v1.0",
                "milestone_id": 500.0,
                "milestone_due_date": pd.Timestamp("2026-11-15"),
                "milestone_start_date": pd.Timestamp("2026-10-01"),
                "age_days": 20,
                "cycle_time": 5.0,
                "is_stale": False,
                "issue_type": "Task",
                "impact": None,
                "priority": "P1",
                "priority_rank": 0.0,
                "team": "default",
                "stage": "Done",
                "stage_type": "completed",
                "stage_order": 5,
                "days_in_stage": 1,
                "context": None,
            },
        ]
    )
    issues_df.to_parquet(analytics_dir / "issues_valid.parquet", engine="pyarrow")
    return analytics_dir, processed_dir, state_file, rules_dir


def test_dashboard_service_collapses_contexts_and_enriches_payload(tmp_path: Path) -> None:
    analytics_dir, processed_dir, state_file, rules_dir = _write_fixture_data(tmp_path)
    service = DashboardService(
        analytics_path=analytics_dir,
        processed_path=processed_dir,
        state_path=state_file,
        rules_path=rules_dir,
    )

    payload = service.get_dashboard_payload()

    assert len(payload.issues) == 2
    first, second = payload.issues
    assert first.id == 1
    assert first.contexts == ["project::A", "project::B"]
    assert first.assignee == "Unassigned"
    assert first.priority == "Unset"
    assert first.parent_id is None
    assert first.child_ids == [11]
    assert first.quality_signals == [
        "MIXED_CLASSIFICATION",
        "UNASSIGNED_OWNER",
        "MISSING_MILESTONE",
    ]
    assert second.id == 2
    assert second.parent_id == 10
    assert second.cycle_time == 5
    assert second.milestone_due_date is not None and second.milestone_due_date.endswith("+00:00")
    assert second.quality_signals == []

    assert payload.filter_options.teams == ["default"]
    assert payload.filter_options.contexts == ["project::A", "project::B"]
    assert payload.filter_options.milestones == ["v1.0"]
    assert payload.filter_options.min_date == "2026-10-15"
    assert payload.filter_options.max_date == "2026-11-01"
    assert payload.palettes.dark["p1"] == "#ff0055"
    assert payload.palettes.light["p1"] == "#cc0044"
    assert payload.palettes.priority_order == ["P1", "P2"]
    assert [s.name for s in payload.stages] == ["Review"]
    assert payload.label_styles["project::A"].color == "#4facfe"
    assert payload.sync_status.status == "1 projects"


def test_dashboard_service_caches_by_mtime_and_clears(tmp_path: Path) -> None:
    analytics_dir, processed_dir, state_file, rules_dir = _write_fixture_data(tmp_path)
    service = DashboardService(
        analytics_path=analytics_dir,
        processed_path=processed_dir,
        state_path=state_file,
        rules_path=rules_dir,
    )

    first = service.get_dashboard_payload()
    second = service.get_dashboard_payload()
    assert first is second

    service.clear_cache()
    third = service.get_dashboard_payload()
    assert third is not first


def _stage_rule(team: str, project_ids: list[int], stage: str, color: str) -> DomainRule:
    return DomainRule(
        team=team,
        project_ids=project_ids,
        workflow=WorkflowConfig(stages=[StageConfig(name=stage)]),
        colors={"global": {"bug": color}},
    )


def test_renamed_default_rule_set_still_provides_colors_and_leads_stages() -> None:
    other = _stage_rule("alpha", [5], "Other", "#111111")
    default = _stage_rule("Platform", [], "First", "#222222")
    rules = {5: other, 0: default}

    assert find_default_rule(rules) is default
    assert resolve_palettes(rules).light["bug"] == "#222222"
    assert [s.name for s in _extract_stages(rules)] == ["First", "Other"]


def test_rules_without_default_keep_team_default_then_first_fallback() -> None:
    named = _stage_rule("default", [5], "Named", "#333333")
    first = _stage_rule("alpha", [6], "Alpha", "#444444")

    assert find_default_rule({6: first, 5: named}) is named
    assert find_default_rule({6: first}) is first
    assert find_default_rule({}) is None
    assert resolve_palettes({6: first}).light["bug"] == "#444444"
    assert [s.name for s in _extract_stages({6: first, 5: named})] == ["Named", "Alpha"]
