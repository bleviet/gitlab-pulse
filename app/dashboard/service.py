"""Cached dashboard data aggregation service for Layer 3."""

import math
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path
from threading import Lock
from typing import Literal

import pandas as pd

from app.dashboard.data_loader import (
    DEFAULT_ANALYTICS_PATH,
    DEFAULT_PROCESSED_PATH,
    DEFAULT_STATE_PATH,
    get_sync_status,
    load_labels,
    load_valid_issues,
)
from app.dashboard.palettes import find_default_rule, resolve_palettes
from app.dashboard.schemas import (
    DashboardPayload,
    FilterOptions,
    IssueItem,
    LabelStyle,
    StageMeta,
    SyncStatus,
)
from app.dashboard.utils import (
    compute_issue_signals_and_hints,
    normalize_assignee_labels,
    normalize_issue_labels,
)
from app.processor.rule_loader import DomainRule, RuleLoader, resolve_rules_path


def _app_version() -> str:
    try:
        return pkg_version("gitlab-pulse")
    except PackageNotFoundError:
        return "0.1.0"


def _is_missing(value: object) -> bool:
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    return isinstance(value, float) and math.isnan(value)


def _to_opt_int(value: object) -> int | None:
    if _is_missing(value):
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    try:
        return int(str(value))
    except ValueError:
        return None


def _to_opt_str(value: object) -> str | None:
    if _is_missing(value):
        return None
    text = str(value).strip()
    if text.lower() in {"", "none", "nan", "<na>", "nat"}:
        return None
    return text


def _to_int_list(value: object) -> list[int]:
    if value is None:
        return []
    tolist = getattr(value, "tolist", None)
    raw = tolist() if callable(tolist) else value
    if not isinstance(raw, (list, tuple)):
        return []
    result: list[int] = []
    for item in raw:
        parsed = _to_opt_int(item)
        if parsed is not None:
            result.append(parsed)
    return result


def _to_iso_utc(value: object) -> str | None:
    if _is_missing(value):
        return None
    if isinstance(value, pd.Timestamp):
        ts = value.tz_localize("UTC") if value.tzinfo is None else value.tz_convert("UTC")
        return str(ts.isoformat())
    if isinstance(value, datetime):
        dt = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
        return dt.isoformat()
    if isinstance(value, str):
        parsed = pd.to_datetime(value, utc=True, errors="coerce")
        if not isinstance(parsed, pd.Timestamp):
            return None
        return str(parsed.isoformat())
    return None


def _collapse_contexts_map(df: pd.DataFrame) -> dict[int, list[str]]:
    if df.empty or "id" not in df.columns or "context" not in df.columns:
        return {}
    pairs = pd.DataFrame(
        {"id": df["id"], "context": df["context"].astype(object)}
    ).dropna(subset=["id", "context"])
    if pairs.empty:
        return {}
    pairs["context"] = pairs["context"].astype(str).str.strip()
    pairs = pairs[pairs["context"] != ""]
    if pairs.empty:
        return {}
    grouped = pairs.groupby("id", sort=False)["context"].agg(
        lambda values: list(dict.fromkeys(values))
    )
    result: dict[int, list[str]] = {}
    for issue_id, contexts in grouped.items():
        parsed_id = _to_opt_int(issue_id)
        if parsed_id is not None:
            result[parsed_id] = contexts
    return result


def _normalize_priority_series(df: pd.DataFrame) -> list[str]:
    if "priority" not in df.columns:
        return ["Unset"] * len(df)
    priority = df["priority"].astype(object)
    text = priority.astype(str).str.strip()
    is_unset = priority.isna() | text.str.lower().isin(["", "none", "nan", "<na>"])
    return [str(val) for val in text.where(~is_unset, "Unset").tolist()]


def _extract_stages(rules: dict[int, DomainRule]) -> list[StageMeta]:
    default_rule = find_default_rule(rules)
    ordered_rules = (
        [default_rule, *[r for r in rules.values() if r is not default_rule]]
        if default_rule is not None
        else list(rules.values())
    )
    stages: list[StageMeta] = []
    seen: set[str] = set()
    for rule in ordered_rules:
        for stage in rule.workflow.stages:
            if stage.name not in seen:
                seen.add(stage.name)
                stages.append(
                    StageMeta(
                        name=stage.name,
                        type=stage.type,
                        description=stage.description,
                    )
                )
    return stages


def _col_list(df: pd.DataFrame, column: str, default: object = None) -> list[object]:
    if column in df.columns:
        return list(df[column].tolist())
    return [default] * len(df)


class DashboardService:
    """Loads Layer 2 analytics Parquet data and caches prepared SPA payloads."""

    def __init__(
        self,
        analytics_path: Path | None = None,
        processed_path: Path | None = None,
        state_path: Path | None = None,
        rules_path: Path | None = None,
    ) -> None:
        self._analytics_path = analytics_path or DEFAULT_ANALYTICS_PATH
        self._processed_path = processed_path or DEFAULT_PROCESSED_PATH
        self._state_path = state_path or DEFAULT_STATE_PATH
        self._rules_path = rules_path
        self._lock = Lock()
        self._cache_key: tuple[tuple[str, int], ...] | None = None
        self._cached_payload: DashboardPayload | None = None

    @property
    def processed_path(self) -> Path:
        """Directory holding the Layer 1 processed Parquet files."""
        return self._processed_path

    def clear_cache(self) -> None:
        """Invalidate the cached dashboard payload."""
        with self._lock:
            self._cache_key = None
            self._cached_payload = None

    def _active_rules_path(self) -> Path:
        return self._rules_path or resolve_rules_path()

    def _compute_mtime_key(self) -> tuple[tuple[str, int], ...]:
        paths: list[Path] = [
            self._analytics_path / "issues_valid.parquet",
            self._state_path,
        ]
        if self._processed_path.exists():
            paths.extend(sorted(self._processed_path.glob("labels_*.parquet")))
        rules_path = self._active_rules_path()
        if rules_path.exists():
            paths.extend(sorted(rules_path.glob("*.yaml")))

        entries: list[tuple[str, int]] = []
        for path in paths:
            try:
                mtime = path.stat().st_mtime_ns if path.exists() else -1
            except OSError:
                mtime = -1
            entries.append((str(path), mtime))
        return tuple(entries)

    def get_dashboard_payload(self) -> DashboardPayload:
        """Return the cached payload or rebuild if source files changed."""
        current_key = self._compute_mtime_key()
        with self._lock:
            if self._cached_payload is not None and self._cache_key == current_key:
                return self._cached_payload

        payload = self._build_payload()
        with self._lock:
            self._cache_key = current_key
            self._cached_payload = payload
        return payload

    def _build_payload(self) -> DashboardPayload:
        df = load_valid_issues(self._analytics_path)
        raw_labels = load_labels(self._processed_path)
        sync_raw = get_sync_status(self._state_path)
        rules = RuleLoader(self._active_rules_path()).rules

        palettes = resolve_palettes(rules)
        stages = _extract_stages(rules)
        label_styles = {
            name: LabelStyle(color=style["color"], text_color=style["text_color"])
            for name, style in raw_labels.items()
        }
        sync_status = SyncStatus(
            status=sync_raw.get("status", "Unknown"),
            last_sync=sync_raw.get("last_sync", "Unknown"),
        )

        if df.empty:
            return DashboardPayload(
                issues=[],
                filter_options=FilterOptions(),
                label_styles=label_styles,
                stages=stages,
                palettes=palettes,
                sync_status=sync_status,
                version=_app_version(),
                generated_at=datetime.now(UTC).isoformat(),
            )

        teams = (
            sorted({str(v) for v in df["team"].dropna().tolist() if str(v).strip()})
            if "team" in df.columns
            else []
        )
        contexts = (
            sorted({str(v) for v in df["context"].dropna().tolist() if str(v).strip()})
            if "context" in df.columns
            else []
        )
        milestones = (
            sorted({str(v) for v in df["milestone"].dropna().tolist() if str(v).strip()})
            if "milestone" in df.columns
            else []
        )
        min_date: str | None = None
        max_date: str | None = None
        if "created_at" in df.columns:
            valid_created = df["created_at"].dropna()
            if not valid_created.empty:
                min_date = str(valid_created.min().date().isoformat())
                max_date = str(valid_created.max().date().isoformat())

        contexts_by_id = _collapse_contexts_map(df)
        unique_df = df.drop_duplicates(subset=["id"]).copy() if "id" in df.columns else df.copy()
        assignees = (
            normalize_assignee_labels(unique_df["assignee"]).tolist()
            if "assignee" in unique_df.columns
            else ["Unassigned"] * len(unique_df)
        )
        priorities = _normalize_priority_series(unique_df)

        issues: list[IssueItem] = []
        for (
            raw_id,
            raw_iid,
            raw_project_id,
            raw_title,
            raw_state,
            raw_created,
            raw_updated,
            raw_closed,
            raw_issue_labels,
            raw_wit,
            raw_parent,
            raw_children,
            raw_url,
            assignee,
            raw_milestone,
            raw_milestone_id,
            raw_ms_due,
            raw_ms_start,
            raw_age,
            raw_cycle,
            raw_stale,
            raw_type,
            raw_impact,
            priority,
            raw_prio_rank,
            raw_team,
            raw_stage,
            raw_stage_type,
            raw_stage_order,
            raw_days_in_stage,
        ) in zip(
            _col_list(unique_df, "id", 0),
            _col_list(unique_df, "iid", 0),
            _col_list(unique_df, "project_id", 0),
            _col_list(unique_df, "title", ""),
            _col_list(unique_df, "state", "opened"),
            _col_list(unique_df, "created_at"),
            _col_list(unique_df, "updated_at"),
            _col_list(unique_df, "closed_at"),
            _col_list(unique_df, "labels"),
            _col_list(unique_df, "work_item_type", "ISSUE"),
            _col_list(unique_df, "parent_id"),
            _col_list(unique_df, "child_ids"),
            _col_list(unique_df, "web_url"),
            assignees,
            _col_list(unique_df, "milestone"),
            _col_list(unique_df, "milestone_id"),
            _col_list(unique_df, "milestone_due_date"),
            _col_list(unique_df, "milestone_start_date"),
            _col_list(unique_df, "age_days", 0),
            _col_list(unique_df, "cycle_time"),
            _col_list(unique_df, "is_stale", False),
            _col_list(unique_df, "issue_type"),
            _col_list(unique_df, "impact")
            if "impact" in unique_df.columns
            else _col_list(unique_df, "severity"),
            priorities,
            _col_list(unique_df, "priority_rank"),
            _col_list(unique_df, "team"),
            _col_list(unique_df, "stage", "Backlog"),
            _col_list(unique_df, "stage_type"),
            _col_list(unique_df, "stage_order", 999),
            _col_list(unique_df, "days_in_stage", 0),
            strict=True,
        ):
            issue_id = _to_opt_int(raw_id) or 0
            raw_state_str = _to_opt_str(raw_state) or "opened"
            state_literal: Literal["opened", "closed"] = (
                "closed" if raw_state_str == "closed" else "opened"
            )
            labels_list = normalize_issue_labels(raw_issue_labels)
            milestone_val = _to_opt_str(raw_milestone)
            signals, hints = compute_issue_signals_and_hints(
                state_literal, labels_list, str(assignee), milestone_val
            )
            created_iso = _to_iso_utc(raw_created) or datetime.now(UTC).isoformat()
            updated_iso = _to_iso_utc(raw_updated) or created_iso

            parsed_stage_order = _to_opt_int(raw_stage_order)
            issues.append(
                IssueItem(
                    id=issue_id,
                    iid=_to_opt_int(raw_iid) or 0,
                    project_id=_to_opt_int(raw_project_id) or 0,
                    title=_to_opt_str(raw_title) or "",
                    state=state_literal,
                    created_at=created_iso,
                    updated_at=updated_iso,
                    closed_at=_to_iso_utc(raw_closed),
                    labels=labels_list,
                    contexts=contexts_by_id.get(issue_id, []),
                    work_item_type=_to_opt_str(raw_wit) or "ISSUE",
                    parent_id=_to_opt_int(raw_parent),
                    child_ids=_to_int_list(raw_children),
                    web_url=_to_opt_str(raw_url),
                    assignee=str(assignee),
                    milestone=milestone_val,
                    milestone_id=_to_opt_int(raw_milestone_id),
                    milestone_due_date=_to_iso_utc(raw_ms_due),
                    milestone_start_date=_to_iso_utc(raw_ms_start),
                    age_days=_to_opt_int(raw_age) or 0,
                    cycle_time=_to_opt_int(raw_cycle),
                    is_stale=bool(raw_stale) if not _is_missing(raw_stale) else False,
                    issue_type=_to_opt_str(raw_type),
                    impact=_to_opt_str(raw_impact),
                    priority=str(priority),
                    priority_rank=_to_opt_int(raw_prio_rank),
                    team=_to_opt_str(raw_team),
                    stage=_to_opt_str(raw_stage) or "Backlog",
                    stage_type=_to_opt_str(raw_stage_type),
                    stage_order=parsed_stage_order if parsed_stage_order is not None else 999,
                    days_in_stage=_to_opt_int(raw_days_in_stage) or 0,
                    quality_signals=signals,
                    quality_hints=hints,
                )
            )

        return DashboardPayload(
            issues=issues,
            filter_options=FilterOptions(
                teams=teams,
                contexts=contexts,
                milestones=milestones,
                min_date=min_date,
                max_date=max_date,
            ),
            label_styles=label_styles,
            stages=stages,
            palettes=palettes,
            sync_status=sync_status,
            version=_app_version(),
            generated_at=datetime.now(UTC).isoformat(),
        )
