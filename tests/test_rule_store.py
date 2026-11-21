"""Tests for rule path resolution, the rule store, and rule set validation."""

import re
from pathlib import Path

import pytest

from app.processor.rule_loader import (
    ClassificationMatch,
    ContextRule,
    DomainRule,
    RuleLoader,
    StageConfig,
    load_rule_file,
    resolve_rules_path,
)
from app.processor.rule_store import (
    InvalidRuleSetNameError,
    RevisionConflictError,
    RuleProblem,
    RuleSetExistsError,
    RuleSetNotFoundError,
    RuleStore,
    RuleVersionNotFoundError,
    dump_rule,
    unique_name,
    validate_rule_set,
)

REPO_RULES = Path(__file__).resolve().parents[1] / "app" / "config" / "rules"

TEMPLATE_YAML = """
project_ids: []
team: "default"
classification:
  priority:
    P2:
      labels: ["priority::2"]
    P1:
      labels: ["priority::1"]
    P3:
      labels: ["priority::3"]
workflow:
  stages:
    - name: "Review"
      labels: ["workflow::review"]
      type: "waiting"
""".strip()


def _make_store(tmp_path: Path) -> tuple[RuleStore, Path, Path]:
    template = tmp_path / "template"
    user = tmp_path / "user"
    template.mkdir()
    template.joinpath("default.yaml").write_text(TEMPLATE_YAML, encoding="utf-8")
    template.joinpath("other.yaml").write_text(
        "project_ids: [5]\nteam: other\n", encoding="utf-8"
    )
    return RuleStore(user_path=user, template_path=template), user, template


def _revision(store: RuleStore, name: str) -> str:
    sets, _ = store.list_rule_sets()
    return next(s.revision for s in sets if s.name == name)


def _paths(problems: list[RuleProblem]) -> set[str]:
    return {p.path for p in problems}


def test_resolve_rules_path_prefers_user_dir_with_yaml(tmp_path: Path) -> None:
    user = tmp_path / "user"
    template = tmp_path / "template"
    assert resolve_rules_path(user, template) == template
    user.mkdir()
    assert resolve_rules_path(user, template) == template
    user.joinpath("a.yaml").write_text("team: a\n", encoding="utf-8")
    assert resolve_rules_path(user, template) == user


def test_dump_round_trip_preserves_classification_order(tmp_path: Path) -> None:
    rule = DomainRule(
        classification={
            "priority": {
                "P2": ClassificationMatch(labels=["priority::2"]),
                "P1": ClassificationMatch(labels=["priority::1"]),
                "P3": ClassificationMatch(labels=["priority::3"]),
            }
        },
        team="alpha",
    )
    path = tmp_path / "x.yaml"
    path.write_text(dump_rule(rule), encoding="utf-8")

    loaded = load_rule_file(path)

    assert list(loaded.classification["priority"]) == ["P2", "P1", "P3"]
    exclude = {"label_mappings", "title_patterns"}
    assert loaded.model_dump(exclude=exclude) == rule.model_dump(exclude=exclude)


def test_dump_drops_deprecated_keys_and_migrates_legacy(tmp_path: Path) -> None:
    legacy = tmp_path / "legacy.yaml"
    legacy.write_text(
        """
label_mappings:
  type:
    "type::bug": Bug
title_patterns:
  type:
    Bug: [fix]
contexts:
  method: prefix
  patterns:
    - prefix: "rnd::"
      alias: "R&D"
""".strip(),
        encoding="utf-8",
    )
    rule = load_rule_file(legacy)

    text = dump_rule(rule)

    assert text.startswith("# Managed by the GitLab Pulse settings UI.")
    for key in ("label_mappings", "title_patterns", "method:", "patterns:"):
        assert key not in text
    out = tmp_path / "out.yaml"
    out.write_text(text, encoding="utf-8")
    reloaded = load_rule_file(out)
    assert reloaded.classification["type"]["Bug"].labels == ["type::bug"]
    assert reloaded.classification["type"]["Bug"].title == ["contains:fix"]
    assert [c.name for c in reloaded.contexts.rules] == ["R&D"]


def test_first_write_seeds_user_dir_and_keeps_template(tmp_path: Path) -> None:
    store, user, template = _make_store(tmp_path)
    template_bytes = template.joinpath("default.yaml").read_bytes()
    assert store.source == "template"
    rule = store.list_rule_sets()[0][0].rule
    revision = _revision(store, "default")

    stored = store.write("default", rule.model_copy(update={"team": "edited"}), revision)

    assert store.active_path == user
    assert template.joinpath("default.yaml").read_bytes() == template_bytes
    assert user.joinpath("other.yaml").read_bytes() == template.joinpath(
        "other.yaml"
    ).read_bytes()
    assert load_rule_file(user / "default.yaml").team == "edited"
    assert stored.revision == _revision(store, "default")
    assert list(user.glob("*.tmp")) == []
    assert len(list((user / ".history").glob("default-*.yaml"))) == 1


def test_second_write_creates_history_and_prunes_to_twenty(tmp_path: Path) -> None:
    store, user, _ = _make_store(tmp_path)
    rule = store.list_rule_sets()[0][0].rule
    revision = _revision(store, "default")
    for index in range(23):
        stored = store.write(
            "default", rule.model_copy(update={"team": f"t{index}"}), revision
        )
        revision = stored.revision

    history = sorted((user / ".history").glob("default-*.yaml"))
    assert len(history) == 20
    assert all(re.fullmatch(r"default-\d{8}T\d{12}Z\.yaml", p.name) for p in history)
    assert list((user / ".history").glob("other-*.yaml")) == []


def test_stale_revision_raises_conflict(tmp_path: Path) -> None:
    store, _, _ = _make_store(tmp_path)
    rule = store.list_rule_sets()[0][0].rule
    with pytest.raises(RevisionConflictError):
        store.write("default", rule, "stale")


def test_unknown_name_raises_not_found(tmp_path: Path) -> None:
    store, _, _ = _make_store(tmp_path)
    with pytest.raises(RuleSetNotFoundError):
        store.write("missing", DomainRule(), "x")


@pytest.mark.parametrize("name", ["../x", "A", "", "-a", "a.b", "a\n"])
def test_invalid_names_rejected(tmp_path: Path, name: str) -> None:
    store, _, _ = _make_store(tmp_path)
    with pytest.raises(InvalidRuleSetNameError):
        store.write(name, DomainRule(), "x")


def test_validate_reports_each_check() -> None:
    rule = DomainRule(
        project_ids=[7],
        classification={"type": {" ": ClassificationMatch(labels=["regex:("])}},
    )
    rule.workflow.stages.extend(
        [
            StageConfig(name="", labels=["contains:"]),
            StageConfig(name="A", type="bogus"),
            StageConfig(name="A"),
        ]
    )
    rule.validation.stale_threshold_days = 0
    rule.validation.max_cycle_time_days = 0
    rule.validation.required_labels["Bug"] = ["exact:"]
    others = {"b": DomainRule(project_ids=[7, 8])}

    problems = validate_rule_set(rule, others)
    found = _paths(problems)

    assert {
        "classification.type.0.name",
        "classification.type.0.labels.0",
        "workflow.stages.0.name",
        "workflow.stages.0.labels.0",
        "workflow.stages.1.type",
        "workflow.stages.2.name",
        "validation.required_labels.Bug.0",
        "validation.stale_threshold_days",
        "validation.max_cycle_time_days",
        "project_ids",
    } <= found
    project_problem = next(p for p in problems if p.path == "project_ids")
    assert "'b'" in project_problem.message
    for problem in problems:
        lowered = problem.message.lower()
        assert "yaml" not in lowered and "pydantic" not in lowered


def test_validate_context_patterns_and_duplicates() -> None:
    rule = DomainRule()
    rule.contexts.rules.extend(
        [
            ContextRule(name="X", labels=["regex:["], title=["contains:"]),
            ContextRule(name="X"),
        ]
    )
    found = _paths(validate_rule_set(rule, {}))
    assert {
        "contexts.rules.0.labels.0",
        "contexts.rules.0.title.0",
        "contexts.rules.1.name",
    } <= found


def test_validate_two_default_sets() -> None:
    problems = validate_rule_set(DomainRule(), {"other": DomainRule()})
    assert [p.path for p in problems] == ["project_ids"]
    assert "other" in problems[0].message


def test_validate_repo_default_is_clean() -> None:
    rule = load_rule_file(REPO_RULES / "default.yaml")
    assert validate_rule_set(rule, {}) == []


def test_list_rule_sets_reports_malformed_file(tmp_path: Path) -> None:
    store, _, template = _make_store(tmp_path)
    template.joinpath("broken.yaml").write_text("project_ids: [unclosed\n", encoding="utf-8")

    rule_sets, errors = store.list_rule_sets()

    assert [s.name for s in rule_sets] == ["default", "other"]
    assert list(errors) == ["broken.yaml"]


def test_rule_loader_records_load_errors(tmp_path: Path) -> None:
    tmp_path.joinpath("good.yaml").write_text("team: good\n", encoding="utf-8")
    tmp_path.joinpath("bad.yaml").write_text("project_ids: [unclosed\n", encoding="utf-8")
    loader = RuleLoader(tmp_path)

    assert loader.rules[0].team == "good"
    assert list(loader.load_errors) == ["bad.yaml"]


@pytest.mark.parametrize(
    ("team", "existing", "expected"),
    [
        ("Backend Team", [], "backend-team"),
        ("  R&D / Ops!! ", [], "r-d-ops"),
        ("Zürich", [], "z-rich"),
        ("", [], "rule-set"),
        ("***", [], "rule-set"),
        ("Backend", ["backend"], "backend-2"),
        ("Backend", ["backend", "backend-2"], "backend-3"),
        ("x" * 100, [], "x" * 60),
        ("x" * 59 + " tail", [], "x" * 59),
        ("x" * 100, ["x" * 60], "x" * 60 + "-2"),
    ],
)
def test_unique_name(team: str, existing: list[str], expected: str) -> None:
    name = unique_name(team, existing)
    assert name == expected
    assert re.fullmatch(r"^[a-z0-9][a-z0-9_-]*$", name)


def test_validate_requires_team_name() -> None:
    problems = validate_rule_set(DomainRule(team="  ", project_ids=[1]), {})
    assert [(p.path, p.message) for p in problems] == [
        ("team", "Give this rule set a team name.")
    ]


def test_create_seeds_template_and_writes_atomically(tmp_path: Path) -> None:
    store, user, template = _make_store(tmp_path)

    stored = store.create("new-team", DomainRule(team="New", project_ids=[9]))

    assert store.source == "user"
    assert load_rule_file(user / "new-team.yaml").team == "New"
    assert user.joinpath("default.yaml").read_bytes() == template.joinpath(
        "default.yaml"
    ).read_bytes()
    assert stored.revision == _revision(store, "new-team")
    assert list(user.glob("*.tmp")) == []
    assert not template.joinpath("new-team.yaml").exists()


def test_create_rejects_existing_and_invalid_names(tmp_path: Path) -> None:
    store, _, _ = _make_store(tmp_path)
    with pytest.raises(RuleSetExistsError):
        store.create("default", DomainRule())
    for name in ("../x", "A", ""):
        with pytest.raises(InvalidRuleSetNameError):
            store.create(name, DomainRule())


def test_delete_archives_removes_and_seeds_template(tmp_path: Path) -> None:
    store, user, template = _make_store(tmp_path)
    revision = _revision(store, "other")

    store.delete("other", revision)

    assert not user.joinpath("other.yaml").exists()
    assert user.joinpath("default.yaml").is_file()
    assert len(list((user / ".history").glob("other-*.yaml"))) == 1
    assert template.joinpath("other.yaml").is_file()


def test_delete_stale_revision_and_unknown_name(tmp_path: Path) -> None:
    store, user, _ = _make_store(tmp_path)
    with pytest.raises(RevisionConflictError):
        store.delete("other", "stale")
    assert not user.exists()
    with pytest.raises(RuleSetNotFoundError):
        store.delete("missing", "x")


def _two_saves(store: RuleStore) -> None:
    rule = store.list_rule_sets()[0][0].rule
    revision = _revision(store, "default")
    revision = store.write("default", rule.model_copy(update={"team": "v1"}), revision).revision
    store.write("default", rule.model_copy(update={"team": "v2"}), revision)


def test_list_versions_newest_first_then_template(tmp_path: Path) -> None:
    store, _, _ = _make_store(tmp_path)
    _two_saves(store)

    versions = store.list_versions("default")

    assert [v.kind for v in versions] == ["history", "history", "template"]
    assert versions[0].id > versions[1].id
    assert versions[0].saved_at is not None and versions[0].saved_at.tzinfo is not None
    assert versions[2].id == "template" and versions[2].saved_at is None
    assert [v.kind for v in store.list_versions("other")] == ["template"]


def test_list_versions_without_template_entry_and_no_name_bleed(tmp_path: Path) -> None:
    store, _, template = _make_store(tmp_path)
    template.joinpath("a.yaml").write_text("team: a\n", encoding="utf-8")
    template.joinpath("a-b.yaml").write_text("team: ab\n", encoding="utf-8")
    sets = {s.name: s for s in store.list_rule_sets()[0]}
    store.write("a-b", DomainRule(team="ab2"), sets["a-b"].revision)
    template.joinpath("a.yaml").unlink()

    versions = store.list_versions("a")

    assert versions == []
    assert [v.kind for v in store.list_versions("a-b")] == ["history", "template"]


def test_read_version(tmp_path: Path) -> None:
    store, _, _ = _make_store(tmp_path)
    _two_saves(store)
    versions = store.list_versions("default")

    assert store.read_version("default", versions[0].id).team == "v1"
    assert store.read_version("default", versions[1].id).team == "default"
    assert store.read_version("default", "template").team == "default"


@pytest.mark.parametrize(
    "version_id",
    ["../x", "template/../x", "2026", "20261121T093015Z", "20200101T000000000000Z"],
)
def test_read_version_rejects_bad_or_missing_ids(tmp_path: Path, version_id: str) -> None:
    store, _, _ = _make_store(tmp_path)
    with pytest.raises(RuleVersionNotFoundError):
        store.read_version("default", version_id)


def _colour_paths(colors: dict[str, object]) -> list[str]:
    return [p.path for p in validate_rule_set(DomainRule(colors=colors), {})]


def test_validate_colours_accepts_valid_forms() -> None:
    colors: dict[str, object] = {
        "light": {"bug": "#fff"},
        "Dark": {"bug": "#1A7a62"},
        "global": {"task": "#abc"},
        "primary": "#ff512f",
    }
    assert _colour_paths(colors) == []


def test_validate_colours_reports_exact_paths() -> None:
    colors: dict[str, object] = {
        "light": {"bug": "red", "task": "#12345"},
        "dark": {"bug": 5},
        "global": {"epic": "#ggg"},
        "primary": "blue",
        "neutral": 7,
    }
    assert _colour_paths(colors) == [
        "colors.light.bug",
        "colors.light.task",
        "colors.dark.bug",
        "colors.global.epic",
        "colors.primary",
        "colors.neutral",
    ]
    message = validate_rule_set(DomainRule(colors={"light": {"bug": "red"}}), {})[0].message
    assert message == (
        "Enter a colour as # followed by 3 or 6 letters or digits, for example #1a7a62."
    )


def test_validate_colours_non_mapping_group_cannot_be_read() -> None:
    problems = validate_rule_set(DomainRule(colors={"light": "#fff"}), {})
    assert [(p.path, p.message) for p in problems] == [
        ("colors.light", "This colour setting cannot be read.")
    ]


def test_read_text_returns_path_and_bytes_for_both_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store, user, template = _make_store(tmp_path)
    template.joinpath("default.yaml").write_text("team: \u00fcber\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    path, text = store.read_text("default")
    assert (path, text) == ("template/default.yaml", "team: \u00fcber\n")

    revision = _revision(store, "default")
    store.write("default", DomainRule(team="saved"), revision)
    path, text = store.read_text("default")
    assert path == "user/default.yaml"
    assert text == user.joinpath("default.yaml").read_text(encoding="utf-8")

    monkeypatch.chdir(tmp_path / "template")
    assert store.read_text("default")[0] == (user / "default.yaml").resolve().as_posix()
    with pytest.raises(RuleSetNotFoundError):
        store.read_text("missing")
