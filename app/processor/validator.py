"""Validation engine (The Gatekeeper) for Layer 2.

Validates issues against YAML rules and splits output.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.processor.rule_loader import DomainRule

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of validation with split DataFrames."""

    valid_df: pd.DataFrame
    quality_df: pd.DataFrame


class ErrorCodes:
    """Standard error codes for quality issues."""

    MISSING_LABEL = "MISSING_LABEL"
    CONFLICTING_LABELS = "CONFLICTING_LABELS"
    STALE_WITHOUT_UPDATE = "STALE_WITHOUT_UPDATE"
    ORPHAN_TASK = "ORPHAN_TASK"
    EXCEEDS_CYCLE_TIME = "EXCEEDS_CYCLE_TIME"


def validate_issues(
    df: pd.DataFrame,
    rule: Optional[DomainRule] = None,
) -> ValidationResult:
    """Validate issues against domain rules.

    The Gatekeeper: splits data into valid and quality (failed) DataFrames.

    Args:
        df: Enriched DataFrame with metrics
        rule: Domain rule configuration

    Returns:
        ValidationResult with valid_df and quality_df
    """
    if df.empty:
        return ValidationResult(valid_df=df, quality_df=pd.DataFrame())

    # Track validation errors per row
    errors: list[tuple[int, str, str]] = []  # (index, error_code, message)

    # Validate required labels
    if rule and rule.validation.required_labels:
        for issue_type, required_prefixes in rule.validation.required_labels.items():
            type_mask = df["issue_type"] == issue_type
            for prefix in required_prefixes:
                missing = df[type_mask].apply(
                    lambda row: not _has_label_prefix(row["labels"], prefix),
                    axis=1,
                )
                for idx in df[type_mask][missing].index:
                    errors.append((
                        idx,
                        ErrorCodes.MISSING_LABEL,
                        f"{issue_type} missing required label: {prefix}*",
                    ))

    # Validate conflicting labels (e.g., both type::bug and type::feature)
    type_labels = ["type::bug", "type::feature", "type::task"]

    def count_type_labels(labels: object) -> int:
        if labels is None:
            return 0
        try:
            label_list = list(labels) if not isinstance(labels, list) else labels
        except (TypeError, ValueError):
            return 0
        return sum(
            1 for label in label_list
            if isinstance(label, str) and any(label.startswith(t) for t in type_labels)
        )

    conflict_mask = df["labels"].apply(lambda l: count_type_labels(l) > 1)
    for idx in df[conflict_mask].index:
        errors.append((
            idx,
            ErrorCodes.CONFLICTING_LABELS,
            "Issue has conflicting type labels",
        ))

    # Validate orphan tasks (parent_id refers to non-existent issue)
    if "parent_id" in df.columns:
        task_mask = df["work_item_type"] == "TASK"
        has_parent = df["parent_id"].notna()
        valid_parent_ids = set(df["id"].tolist())

        orphan_mask = task_mask & has_parent & ~df["parent_id"].isin(valid_parent_ids)
        for idx in df[orphan_mask].index:
            errors.append((
                idx,
                ErrorCodes.ORPHAN_TASK,
                f"Task references non-existent parent: {df.loc[idx, 'parent_id']}",
            ))

    # Validate cycle time threshold
    if rule and "cycle_time" in df.columns:
        max_cycle = rule.validation.max_cycle_time_days
        exceeds_mask = df["cycle_time"].notna() & (df["cycle_time"] > max_cycle)
        for idx in df[exceeds_mask].index:
            errors.append((
                idx,
                ErrorCodes.EXCEEDS_CYCLE_TIME,
                f"Cycle time ({df.loc[idx, 'cycle_time']} days) exceeds threshold ({max_cycle})",
            ))

    # Split data based on errors
    if errors:
        error_indices = {e[0] for e in errors}
        valid_df = df[~df.index.isin(error_indices)].copy()

        # Build quality DataFrame with error info
        quality_rows = []
        for idx, error_code, message in errors:
            row = df.loc[idx].to_dict()
            row["error_code"] = error_code
            row["error_message"] = message
            quality_rows.append(row)

        quality_df = pd.DataFrame(quality_rows)
    else:
        valid_df = df.copy()
        quality_df = pd.DataFrame()

    logger.info(f"Validation: {len(valid_df)} valid, {len(quality_df)} failed")
    return ValidationResult(valid_df=valid_df, quality_df=quality_df)


def _has_label_prefix(labels: object, prefix: str) -> bool:
    """Check if any label starts with the given prefix."""
    if labels is None:
        return False

    # Handle numpy arrays, lists, and other iterables
    try:
        label_list = list(labels) if not isinstance(labels, list) else labels
    except (TypeError, ValueError):
        return False

    clean_prefix = prefix.rstrip("*")
    return any(
        isinstance(label, str) and label.startswith(clean_prefix)
        for label in label_list
    )
