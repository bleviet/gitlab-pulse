"""Tests for the dry-run impact preview of a draft rule set."""

from pathlib import Path

import pandas as pd

from app.processor.preview import CountChange, ImpactSummary, summarize_impact
from app.processor.rule_loader import (
    ClassificationMatch,
    ContextRule,
    DomainRule,
    RuleLoader,
    StageConfig,
    load_rule_file,
)

TODAY_YAML = """
project_ids: []
team: "default"
classification:
  type:
    Bug:
      labels: ["type::bug"]
workflow:
  stages:
    - name: "Review"
      labels: ["workflow::review"]
    - name: "Testing"
      labels: ["workflow::test"]
contexts:
  rules:
    - name: "A"
      labels: ["contains:project::A"]
    - name: "B"
      labels: ["contains:project::B"]
validation:
  stale_threshold_days: 30
""".strip()

# (id, state, labels, title, days since update)
ROWS: list[tuple[int, str, list[str], str, int]] = [
    (1, "opened", ["type::bug", "workflow::review"], "Crash on start", 20),
    (2, "opened", ["kind::defect"], "Odd defect", 20),
    (3, "opened", ["workflow::review", "workflow::test", "project::A", "project::B"], "Multi", 20),
    (4, "closed", ["type::bug"], "Old bug", 20),
]


def _write_project(
    processed: Path,
    project_id: int,
    rows: list[tuple[int, str, list[str], str, int]],
) -> None:
    now = pd.Timestamp.now(tz="UTC")
    df = pd.DataFrame(
        {
            "id": [r[0] for r in rows],
            "iid": [r[0] for r in rows],
            "project_id": project_id,
            "title": [r[3] for r in rows],
            "state": [r[1] for r in rows],
            "created_at": now - pd.Timedelta(days=60),
            "updated_at": [now - pd.Timedelta(days=r[4]) for r in rows],
            "closed_at": [now if r[1] == "closed" else pd.NaT for r in rows],
            "labels": [r[2] for r in rows],
            "work_item_type": "ISSUE",
            "parent_id": float("nan"),
            "assignee": "someone",
        }
    )
    processed.mkdir(parents=True, exist_ok=True)
    df.to_parquet(processed / f"issues_{project_id}.parquet")


def _setup(tmp_path: Path) -> tuple[Path, Path, DomainRule]:
    processed = tmp_path / "processed"
    _write_project(processed, 1, ROWS)
    rules = tmp_path / "rules"
    rules.mkdir()
    rules.joinpath("default.yaml").write_text(TODAY_YAML, encoding="utf-8")
    return processed, rules, load_rule_file(rules / "default.yaml")


def _by_name(changes: list[CountChange]) -> dict[str | None, tuple[int, int]]:
    return {c.name: (c.before, c.after) for c in changes}


def test_adding_label_moves_issues_from_unset_to_type(tmp_path: Path) -> None:
    processed, rules, draft = _setup(tmp_path)
    draft.classification["type"]["Bug"].labels.append("kind::defect")

    impact = summarize_impact(processed, rules, "default", draft, {})

    assert [(c.name, c.before, c.after) for c in impact.types] == [
        ("Bug", 2, 3),
        (None, 2, 1),
    ]
    assert impact.total_issues == 4
    assert impact.project_ids == [1]


def test_reordering_stages_changes_stage_and_backlog_first_done_last(tmp_path: Path) -> None:
    processed, rules, draft = _setup(tmp_path)
    draft.workflow.stages.reverse()

    impact = summarize_impact(processed, rules, "default", draft, {})

    assert [(c.name, c.before, c.after) for c in impact.stages] == [
        ("Backlog", 1, 1),
        ("Testing", 0, 1),
        ("Review", 2, 1),
        ("Done", 1, 1),
    ]


def test_lower_stale_threshold_raises_stale_after_count(tmp_path: Path) -> None:
    processed, rules, draft = _setup(tmp_path)
    draft.validation.stale_threshold_days = 10

    impact = summarize_impact(processed, rules, "default", draft, {})

    assert [(c.name, c.before, c.after) for c in impact.quality] == [("STALE", 0, 3)]


def test_counts_use_distinct_issue_ids_when_contexts_explode(tmp_path: Path) -> None:
    processed, rules, draft = _setup(tmp_path)

    impact = summarize_impact(processed, rules, "default", draft, {})

    assert [(c.name, c.before, c.after) for c in impact.contexts] == [
        ("A", 1, 1),
        ("B", 1, 1),
        (None, 3, 3),
    ]
    assert sum(c.after for c in impact.types) == 4


def test_governed_projects_default_draft_skips_claimed_projects(tmp_path: Path) -> None:
    processed, rules, draft = _setup(tmp_path)
    _write_project(processed, 2, [(20, "opened", [], "Other", 1)])
    _write_project(processed, 3, [(30, "opened", [], "Third", 1)])
    others = {"x": DomainRule(project_ids=[2])}

    impact = summarize_impact(processed, rules, "default", draft, others)

    assert impact.project_ids == [1, 3]
    assert impact.total_issues == 5


def test_governed_projects_explicit_ids(tmp_path: Path) -> None:
    processed, rules, draft = _setup(tmp_path)
    _write_project(processed, 2, [(20, "opened", [], "Other", 1)])
    draft.project_ids = [2, 99]

    impact = summarize_impact(processed, rules, "default", draft, {})

    assert impact.project_ids == [2]
    assert impact.total_issues == 1


def test_before_uses_project_specific_rule(tmp_path: Path) -> None:
    processed, rules, draft = _setup(tmp_path)
    _write_project(processed, 2, [(20, "opened", ["only::mine"], "Other", 1)])
    rules.joinpath("p2.yaml").write_text(
        'project_ids: [2]\nclassification:\n  type:\n    Mine:\n      labels: ["only::mine"]\n',
        encoding="utf-8",
    )
    assert RuleLoader(rules).get_rule(2) is not None
    draft.project_ids = [2]

    impact = summarize_impact(processed, rules, "default", draft, {})

    assert [(c.name, c.before, c.after) for c in impact.types] == [
        ("Mine", 1, 0),
        (None, 0, 1),
    ]


def test_pattern_counts(tmp_path: Path) -> None:
    processed, rules, draft = _setup(tmp_path)
    draft.classification["type"]["Bug"].title = ["contains:Crash", "regex:^Old", "contains:zzz"]
    draft.classification["type"]["Bug"].labels = ["type::bug", "exact:none", "regex:^workflow::"]
    draft.validation.required_labels = {"Bug": ["contains:kind"]}

    impact = summarize_impact(processed, rules, "default", draft, {})

    assert impact.label_pattern_counts["type::bug"] == 2
    assert impact.label_pattern_counts["exact:none"] == 0
    assert impact.label_pattern_counts["regex:^workflow::"] == 2
    assert impact.label_pattern_counts["contains:kind"] == 1
    assert impact.label_pattern_counts["contains:project::A"] == 1
    assert impact.title_pattern_counts == {
        "contains:Crash": 1,
        "regex:^Old": 1,
        "contains:zzz": 0,
    }


def test_unmapped_labels_are_sorted_and_capped(tmp_path: Path) -> None:
    processed, rules, draft = _setup(tmp_path)
    many = [f"lbl{i:03d}" for i in range(120)]
    _write_project(
        processed,
        1,
        [*ROWS, (5, "opened", many, "Many", 1), (6, "opened", ["kind::defect"], "Dup", 1)],
    )

    impact = summarize_impact(processed, rules, "default", draft, {})

    assert impact.unmapped_label_total == 121
    assert len(impact.unmapped_labels) == 100
    assert (impact.unmapped_labels[0].name, impact.unmapped_labels[0].count) == ("kind::defect", 2)
    assert [u.name for u in impact.unmapped_labels[1:4]] == ["lbl000", "lbl001", "lbl002"]
    assert "workflow::review" not in {u.name for u in impact.unmapped_labels}


def test_rows_with_no_change_are_omitted_and_nothing_is_written(tmp_path: Path) -> None:
    processed, rules, draft = _setup(tmp_path)
    draft.classification["type"]["Feature"] = ClassificationMatch(labels=["type::feature"])
    draft.workflow.stages.append(StageConfig(name="Empty", labels=["nope"]))
    draft.contexts.rules.append(ContextRule(name="Unused", labels=["nope"]))
    snapshot = sorted((str(p), p.stat().st_size) for p in tmp_path.rglob("*"))

    impact = summarize_impact(processed, rules, "default", draft, {})

    assert isinstance(impact, ImpactSummary)
    assert "Feature" not in _by_name(impact.types)
    assert "Empty" not in _by_name(impact.stages)
    assert "Unused" not in _by_name(impact.contexts)
    assert sorted((str(p), p.stat().st_size) for p in tmp_path.rglob("*")) == snapshot


def test_default_draft_sorting_after_another_default_governs_nothing(
    tmp_path: Path,
) -> None:
    processed, rules, draft = _setup(tmp_path)
    rules.joinpath("a_team.yaml").write_text("team: a_team\n", encoding="utf-8")
    other = load_rule_file(rules / "a_team.yaml")
    rule = RuleLoader(rules).get_rule(1)
    assert rule is not None and rule.team == "a_team"

    impact = summarize_impact(processed, rules, "default", draft, {"a_team": other})

    assert impact.project_ids == []
    assert impact.total_issues == 0
    assert impact.types == [] and impact.stages == [] and impact.contexts == []


def test_default_draft_sorting_before_another_default_governs_all(
    tmp_path: Path,
) -> None:
    processed, rules, draft = _setup(tmp_path)
    rules.joinpath("z_team.yaml").write_text("team: z_team\n", encoding="utf-8")
    other = load_rule_file(rules / "z_team.yaml")
    rule = RuleLoader(rules).get_rule(1)
    assert rule is not None and rule.team == "default"

    impact = summarize_impact(processed, rules, "default", draft, {"z_team": other})

    assert impact.project_ids == [1]
    assert impact.total_issues == 4


def test_default_other_does_not_block_draft_with_explicit_projects(
    tmp_path: Path,
) -> None:
    processed, rules, draft = _setup(tmp_path)
    draft.project_ids = [1]

    impact = summarize_impact(
        processed, rules, "z_team", draft, {"a_team": DomainRule()}
    )

    assert impact.project_ids == [1]
