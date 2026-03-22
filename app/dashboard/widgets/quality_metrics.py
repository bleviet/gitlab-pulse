"""Helpers for quality hint summary metrics."""

from typing import Any

import pandas as pd


def _extract_issue_ids(df: pd.DataFrame) -> set[Any] | None:
    """Return unique non-null issue ids when the frame exposes an ``id`` column."""
    if "id" not in df.columns:
        return None
    return set(df["id"].dropna().tolist())


def compute_quality_summary(
    valid_df: pd.DataFrame,
    quality_df: pd.DataFrame,
) -> dict[str, int | float]:
    """Compute summary counts for hint-based quality reporting."""
    valid_ids = _extract_issue_ids(valid_df)
    quality_ids = _extract_issue_ids(quality_df)

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
