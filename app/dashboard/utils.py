"""Pure data-normalization, quality-hint, and hierarchy utilities."""

import ast
import math
import re
from urllib.parse import parse_qs, urlparse

import pandas as pd

SIGNAL_UNASSIGNED_OWNER = "UNASSIGNED_OWNER"
SIGNAL_MISSING_MILESTONE = "MISSING_MILESTONE"
SIGNAL_MIXED_CLASSIFICATION = "MIXED_CLASSIFICATION"

_CLASSIFICATION_GROUPS: tuple[tuple[str, str], ...] = (
    ("type::", "Mixed type labels"),
    ("severity::", "Mixed severity labels"),
    ("priority::", "Mixed priority labels"),
)


def normalize_assignee_labels(series: pd.Series) -> pd.Series:
    """Normalize assignee values for display and filtering."""
    return (
        series.fillna("Unassigned")
        .astype(str)
        .str.strip()
        .replace(
            {
                "": "Unassigned",
                "nan": "Unassigned",
                "<NA>": "Unassigned",
                "None": "Unassigned",
            }
        )
    )


def normalize_issue_labels(raw_labels: object) -> list[str]:
    """Normalize labels from Parquet/array/string forms into a clean list."""
    if raw_labels is None:
        return []

    def _clean(values: list[object]) -> list[str]:
        return [
            str(value).strip()
            for value in values
            if str(value).strip().lower() not in ("", "nan", "none", "<na>")
        ]

    if isinstance(raw_labels, (list, tuple)):
        return _clean(list(raw_labels))

    tolist = getattr(raw_labels, "tolist", None)
    if callable(tolist):
        converted = tolist()
        if isinstance(converted, list):
            return _clean(converted)

    raw = str(raw_labels).strip()
    if raw.lower() in ("", "nan", "none", "[]", "<na>"):
        return []

    try:
        parsed = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        parsed = None

    quoted_values = re.findall(r"'([^']+)'|\"([^\"]+)\"", raw)
    if len(quoted_values) > 1:
        return _clean([first or second for first, second in quoted_values])

    if isinstance(parsed, list):
        return _clean(parsed)

    if isinstance(parsed, tuple):
        return _clean(list(parsed))

    return [raw]


def mixed_classification_hints(labels: list[str]) -> list[str]:
    """Describe conflicting classification labels carried by an issue."""
    hints: list[str] = []
    for prefix, group_label in _CLASSIFICATION_GROUPS:
        matches = [label for label in labels if label.lower().startswith(prefix)]
        if len(matches) > 1:
            hints.append(f"{group_label}: {' + '.join(matches)}")
    return hints


def is_missing_milestone(value: object) -> bool:
    """Return True when milestone information is absent."""
    if value is None or value is pd.NA or value is pd.NaT:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip().lower() in {"", "none", "nan", "<na>"}


def compute_issue_signals_and_hints(
    state: str,
    labels: list[str],
    assignee: str,
    milestone: object,
) -> tuple[list[str], list[str]]:
    """Compute quality signal codes and human-readable hint strings for an issue."""
    if state != "opened":
        return ([], [])

    signals: list[str] = []
    hints = mixed_classification_hints(labels)
    if hints:
        signals.append(SIGNAL_MIXED_CLASSIFICATION)

    if assignee == "Unassigned":
        signals.append(SIGNAL_UNASSIGNED_OWNER)
        hints.append("Unassigned owner")

    if is_missing_milestone(milestone):
        signals.append(SIGNAL_MISSING_MILESTONE)
        hints.append("Missing milestone")

    return (signals, hints)


def is_local_issue_url(url: object) -> bool:
    """Return True when a URL points to a synthetic local dashboard issue."""
    if not isinstance(url, str) or not url:
        return False
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    return query.get("issue_source", [""])[0] == "local"


def sort_hierarchy(
    df: pd.DataFrame,
    parent_col: str = "parent_id",
    id_col: str = "id",
    title_col: str = "title",
) -> pd.DataFrame:
    """Sort DataFrame hierarchically: parent followed by indented children."""
    if df.empty or parent_col not in df.columns:
        return df

    children_map: dict[object, list[object]] = {}
    all_ids = set(df[id_col])
    parent_series = df[parent_col]
    is_root = parent_series.isna() | ~parent_series.isin(all_ids)
    roots = df.index[is_root].tolist()

    child_df = df[~is_root]
    for idx, pid in zip(child_df.index, child_df[parent_col], strict=True):
        children_map.setdefault(pid, []).append(idx)

    ordered_indices: list[tuple[object, int]] = []
    ids: dict[object, object] = dict(zip(df.index, df[id_col], strict=True))
    titles: dict[object, object] = dict(zip(df.index, df[title_col], strict=True))

    def dfs(idx: object, level: int) -> None:
        ordered_indices.append((idx, level))
        row_id = ids[idx]
        for child_idx in children_map.get(row_id, []):
            dfs(child_idx, level + 1)

    for root_idx in roots:
        dfs(root_idx, 0)

    if not ordered_indices:
        return df

    new_order = [x[0] for x in ordered_indices]
    sorted_df = df.loc[new_order].copy()

    def _format_title(title: object, level: int) -> str:
        if level > 0:
            prefix = "    " * level + "↳ "
            return f"{prefix}{title}"
        return str(title)

    sorted_df[title_col] = [
        _format_title(titles[idx], level) for idx, level in ordered_indices
    ]
    return sorted_df


def compute_quality_summary(
    valid_df: pd.DataFrame,
    quality_df: pd.DataFrame,
) -> dict[str, int | float]:
    """Compute summary counts for hint-based quality reporting."""
    valid_ids = (
        set(valid_df["id"].dropna().tolist())
        if "id" in valid_df.columns
        else None
    )
    quality_ids = (
        set(quality_df["id"].dropna().tolist())
        if "id" in quality_df.columns
        else None
    )

    if valid_ids is not None or quality_ids is not None:
        all_issue_ids = (valid_ids or set()) | (quality_ids or set())
        total_issues = len(all_issue_ids)
        flagged_issues = len(quality_ids or set())
    else:
        total_issues = len(valid_df) if not valid_df.empty else len(quality_df)
        flagged_issues = min(len(quality_df), total_issues)

    clean_issues = max(total_issues - flagged_issues, 0)
    score = round((clean_issues / total_issues) * 100, 1) if total_issues else 0.0

    return {
        "total_issues": total_issues,
        "flagged_issues": flagged_issues,
        "clean_issues": clean_issues,
        "score": score,
    }
