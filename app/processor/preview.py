"""Dry-run impact preview of a draft rule set (Layer 2, read-only).

Runs the processing pipeline on the processed issue data twice, once with the
rules in use today and once with the draft, and reports what would change.
Nothing is written to disk.
"""

from collections.abc import Iterable, Mapping
from functools import partial
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ConfigDict

from app.processor.main import process_issues
from app.processor.rule_loader import DomainRule, RuleLoader
from app.processor.rule_store import effective_default_name
from app.processor.utils import match_text

UNMAPPED_LABEL_LIMIT = 100
STALE_ROW_NAME = "STALE"


class CountChange(BaseModel):
    """Distinct issue counts for one value before and after the draft."""

    model_config = ConfigDict(frozen=True)

    name: str | None
    before: int
    after: int


class UnmappedLabel(BaseModel):
    """A label that no pattern of the draft maps, with its issue count."""

    model_config = ConfigDict(frozen=True)

    name: str
    count: int


class ImpactSummary(BaseModel):
    """What a draft rule set would change for the projects it governs."""

    model_config = ConfigDict(frozen=True)

    total_issues: int
    project_ids: list[int]
    types: list[CountChange]
    severities: list[CountChange]
    priorities: list[CountChange]
    stages: list[CountChange]
    contexts: list[CountChange]
    quality: list[CountChange]
    unmapped_labels: list[UnmappedLabel]
    unmapped_label_total: int
    label_pattern_counts: dict[str, int]
    title_pattern_counts: dict[str, int]


def _project_id(filepath: Path) -> int | None:
    try:
        return int(filepath.stem.split("_")[1])
    except (IndexError, ValueError):
        return None


def _governed_projects(
    processed_path: Path,
    name: str,
    draft: DomainRule,
    others: Mapping[str, DomainRule],
) -> dict[int, Path]:
    if not draft.project_ids and effective_default_name({**others, name: draft}) != name:
        return {}
    claimed = {pid for rule in others.values() for pid in rule.project_ids}
    governed: dict[int, Path] = {}
    for filepath in sorted(processed_path.glob("issues_*.parquet")):
        project_id = _project_id(filepath)
        if project_id is None:
            continue
        if draft.project_ids:
            if project_id in draft.project_ids:
                governed[project_id] = filepath
        elif project_id not in claimed:
            governed[project_id] = filepath
    return governed


def _removed_projects(
    processed_path: Path, draft: DomainRule, saved: DomainRule | None
) -> dict[int, Path]:
    if saved is None:
        return {}
    removed = set(saved.project_ids) - set(draft.project_ids)
    return {
        project_id: processed_path / f"issues_{project_id}.parquet"
        for project_id in sorted(removed)
        if (processed_path / f"issues_{project_id}.parquet").is_file()
    }


def _concat(frames: list[pd.DataFrame]) -> pd.DataFrame:
    non_empty = [frame for frame in frames if not frame.empty]
    return pd.concat(non_empty, ignore_index=True) if non_empty else pd.DataFrame()


def _distinct_counts(df: pd.DataFrame, column: str) -> dict[str | None, int]:
    if df.empty or column not in df.columns or "id" not in df.columns:
        return {}
    pairs = df[["id", column]].drop_duplicates()
    counts = pairs.groupby(column, dropna=False, observed=True)["id"].nunique()
    return {
        (None if key is None or key != key else str(key)): int(count)
        for key, count in counts.items()
    }


def _stale_count(valid: pd.DataFrame) -> dict[str | None, int]:
    if valid.empty or "is_stale" not in valid.columns:
        return {}
    stale = valid["is_stale"].fillna(False).astype(bool) & (valid["state"] == "opened")
    count = int(valid.loc[stale, "id"].nunique())
    return {STALE_ROW_NAME: count} if count else {}


def _changes(
    before: dict[str | None, int],
    after: dict[str | None, int],
    draft_order: Iterable[str],
    trailing: tuple[str, ...] = (),
) -> list[CountChange]:
    names = set(before) | set(after)
    ordered: list[str | None] = []
    for name in draft_order:
        if name in names and name not in ordered:
            ordered.append(name)
    ordered.extend(
        sorted(n for n in names if n is not None and n not in ordered and n not in trailing)
    )
    ordered.extend(n for n in trailing if n in names and n not in ordered)
    if None in names:
        ordered.append(None)
    return [
        CountChange(name=name, before=before.get(name, 0), after=after.get(name, 0))
        for name in ordered
        if before.get(name, 0) or after.get(name, 0)
    ]


def _label_pairs(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty or "labels" not in raw.columns:
        return pd.DataFrame({"id": pd.Series(dtype="int64"), "labels": pd.Series(dtype=object)})
    pairs = raw[["id", "labels"]].explode("labels").dropna(subset=["labels"])
    is_text = pairs["labels"].map(lambda label: isinstance(label, str)).astype(bool)
    return pairs[is_text].drop_duplicates()


def _matching_labels(labels: pd.Series, patterns: Iterable[str]) -> set[str]:
    patterns = list(patterns)
    return {
        label
        for label in labels.unique()
        if any(match_text(label, pattern) for pattern in patterns)
    }


def _label_patterns(draft: DomainRule) -> list[str]:
    patterns: list[str] = []
    for values in draft.classification.values():
        for match in values.values():
            patterns.extend(match.labels)
    for stage in draft.workflow.stages:
        patterns.extend(stage.labels)
    for context in draft.contexts.rules:
        patterns.extend(context.labels)
    return patterns


def _title_patterns(draft: DomainRule) -> list[str]:
    patterns: list[str] = []
    for values in draft.classification.values():
        for match in values.values():
            patterns.extend(match.title)
    for context in draft.contexts.rules:
        patterns.extend(context.title)
    return patterns


def _title_matches(title: object, pattern: str) -> bool:
    return isinstance(title, str) and match_text(title, pattern) is not None


def _title_pattern_counts(raw: pd.DataFrame, patterns: list[str]) -> dict[str, int]:
    if raw.empty or "title" not in raw.columns:
        return {pattern: 0 for pattern in dict.fromkeys(patterns)}
    titles = raw[["id", "title"]].drop_duplicates("id")["title"]
    counts: dict[str, int] = {}
    for pattern in dict.fromkeys(patterns):
        matched = titles.map(partial(_title_matches, pattern=pattern))
        counts[pattern] = int(matched.sum())
    return counts


def summarize_impact(
    processed_path: Path,
    rules_path: Path,
    name: str,
    draft: DomainRule,
    others: Mapping[str, DomainRule],
    saved: DomainRule | None = None,
) -> ImpactSummary:
    """Compare today's rules with a draft over the processed issue data.

    Args:
        processed_path: Directory holding ``issues_<project_id>.parquet`` files
        rules_path: Directory of the rules used by the processor today
        name: Name (file stem) of the rule set being edited
        draft: The rule set being edited
        others: The other rule sets by name, excluding the one being edited
        saved: The stored version of the rule set being edited, if any. Projects
            it lists that the draft drops are compared against the default rules
            they would fall back to.

    Returns:
        Distinct-issue counts before and after, pattern hit counts, and labels
        no pattern of the draft maps.

    Raises:
        ConfigurationConflictError: If two rule files claim the same project
    """
    governed = _governed_projects(processed_path, name, draft, others)
    removed = _removed_projects(processed_path, draft, saved)
    default_name = effective_default_name(others)
    fallback = others[default_name] if default_name is not None else DomainRule()
    loader = RuleLoader(rules_path)

    raw_frames: list[pd.DataFrame] = []
    before_valid: list[pd.DataFrame] = []
    before_quality: list[pd.DataFrame] = []
    after_valid: list[pd.DataFrame] = []
    after_quality: list[pd.DataFrame] = []
    all_issues: list[pd.DataFrame] = []
    for project_id, filepath in [*governed.items(), *removed.items()]:
        raw = pd.read_parquet(filepath)
        all_issues.append(raw)
        if project_id in governed:
            raw_frames.append(raw)
        current = loader.get_rule(project_id) or loader.get_default_rule()
        valid, quality = process_issues(raw.copy(), current)
        before_valid.append(valid)
        before_quality.append(quality)
        valid, quality = process_issues(
            raw.copy(), draft if project_id in governed else fallback
        )
        after_valid.append(valid)
        after_quality.append(quality)

    raw_all = _concat(raw_frames)
    issues_all = _concat(all_issues)
    before_v, before_q = _concat(before_valid), _concat(before_quality)
    after_v, after_q = _concat(after_valid), _concat(after_quality)

    def change(
        column: str, order: Iterable[str], frames: tuple[pd.DataFrame, pd.DataFrame]
    ) -> list[CountChange]:
        return _changes(
            _distinct_counts(frames[0], column), _distinct_counts(frames[1], column), order
        )

    valid_pair = (before_v, after_v)
    quality_before = _distinct_counts(before_q, "error_code")
    quality_before.update(_stale_count(before_v))
    quality_after = _distinct_counts(after_q, "error_code")
    quality_after.update(_stale_count(after_v))

    pairs = _label_pairs(raw_all)
    label_patterns = _label_patterns(draft)
    required = [p for patterns in draft.validation.required_labels.values() for p in patterns]
    label_pattern_counts = {
        pattern: int(
            pairs.loc[
                pairs["labels"].isin(_matching_labels(pairs["labels"], [pattern])), "id"
            ].nunique()
        )
        for pattern in dict.fromkeys([*label_patterns, *required])
    }

    mapped = _matching_labels(pairs["labels"], label_patterns)
    unmapped_pairs = pairs[~pairs["labels"].isin(mapped)]
    unmapped_counts = unmapped_pairs.groupby("labels")["id"].nunique()
    unmapped = sorted(
        ((str(label), int(count)) for label, count in unmapped_counts.items()),
        key=lambda item: (-item[1], item[0]),
    )

    return ImpactSummary(
        total_issues=int(issues_all["id"].nunique()) if not issues_all.empty else 0,
        project_ids=sorted([*governed, *removed]),
        types=change("issue_type", draft.classification.get("type", {}), valid_pair),
        severities=change("severity", draft.classification.get("severity", {}), valid_pair),
        priorities=change("priority", draft.classification.get("priority", {}), valid_pair),
        stages=_changes(
            _distinct_counts(before_v, "stage"),
            _distinct_counts(after_v, "stage"),
            ["Backlog", *(stage.name for stage in draft.workflow.stages)],
            trailing=("Done",),
        ),
        contexts=change(
            "context_group", [ctx.name for ctx in draft.contexts.rules], valid_pair
        ),
        quality=_changes(quality_before, quality_after, []),
        unmapped_labels=[
            UnmappedLabel(name=name, count=count)
            for name, count in unmapped[:UNMAPPED_LABEL_LIMIT]
        ],
        unmapped_label_total=len(unmapped),
        label_pattern_counts=label_pattern_counts,
        title_pattern_counts=_title_pattern_counts(raw_all, _title_patterns(draft)),
    )
