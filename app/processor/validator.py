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
    MISSING_FIELD = "MISSING_FIELD"
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

    Note: Only OPEN issues are validated. Closed issues are historical records
    and hygiene checks are not actionable, so they pass through without validation.

    Args:
        df: Enriched DataFrame with metrics
        rule: Domain rule configuration

    Returns:
        ValidationResult with valid_df and quality_df
    """
    if df.empty:
        return ValidationResult(valid_df=df, quality_df=pd.DataFrame())

    # Separate open and closed issues - only validate open issues
    # Closed issues are historical records; hygiene checks are not actionable
    if "state" in df.columns:
        open_df = df[df["state"] == "opened"].copy()
        closed_df = df[df["state"] != "opened"].copy()
        logger.debug(f"Validation scope: {len(open_df)} open, {len(closed_df)} closed (skipped)")
    else:
        open_df = df.copy()
        closed_df = pd.DataFrame()

    # If no open issues to validate, return all as valid
    if open_df.empty:
        return ValidationResult(valid_df=df.copy(), quality_df=pd.DataFrame())

    # Track validation errors per row (only for open issues)
    errors: list[tuple[int, str, str]] = []  # (index, error_code, message)

    # Validate required labels
    if rule and rule.validation.required_labels:
        for issue_type, required_prefixes in rule.validation.required_labels.items():
            type_mask = open_df["issue_type"] == issue_type
            for prefix in required_prefixes:
                missing = open_df[type_mask].apply(
                    lambda row: not _has_label_prefix(row["labels"], prefix),
                    axis=1,
                )
                for idx in open_df[type_mask][missing].index:
                    errors.append((
                        idx,
                        ErrorCodes.MISSING_LABEL,
                        f"{issue_type} missing required label: {prefix}*",
                    ))

    # Validate required fields
    if rule and rule.validation.required_fields:
        for issue_type, required_cols in rule.validation.required_fields.items():
            type_mask = open_df["issue_type"] == issue_type
            if not type_mask.any():
                continue

            for col in required_cols:
                if col not in open_df.columns:
                    logger.warning(f"Required field '{col}' not found in DataFrame - check enrichment")
                    # Optionally fail all issues of this type? For now just log warning.
                    continue

                # Check for null, NaN, or empty string
                missing_mask = open_df[type_mask][col].isna() | (open_df[type_mask][col] == "")

                for idx in open_df[type_mask][missing_mask].index:
                    errors.append((
                        idx,
                        ErrorCodes.MISSING_FIELD,
                        f"{issue_type} missing required field: {col}",
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

    conflict_mask = open_df["labels"].apply(lambda l: count_type_labels(l) > 1)
    for idx in open_df[conflict_mask].index:
        errors.append((
            idx,
            ErrorCodes.CONFLICTING_LABELS,
            "Issue has conflicting type labels",
        ))

    # Validate orphan tasks (parent_id refers to non-existent issue)
    # Note: We check against ALL issues (open + closed) for valid parent IDs
    if "parent_id" in open_df.columns:
        task_mask = open_df["work_item_type"] == "TASK"
        has_parent = open_df["parent_id"].notna()
        valid_parent_ids = set(df["id"].tolist())  # Use full df for parent lookup

        orphan_mask = task_mask & has_parent & ~open_df["parent_id"].isin(valid_parent_ids)
        for idx in open_df[orphan_mask].index:
            errors.append((
                idx,
                ErrorCodes.ORPHAN_TASK,
                f"Task references non-existent parent: {open_df.loc[idx, 'parent_id']}",
            ))

    # Validate cycle time threshold
    if rule and "cycle_time" in open_df.columns:
        max_cycle = rule.validation.max_cycle_time_days
        exceeds_mask = open_df["cycle_time"].notna() & (open_df["cycle_time"] > max_cycle)
        for idx in open_df[exceeds_mask].index:
            errors.append((
                idx,
                ErrorCodes.EXCEEDS_CYCLE_TIME,
                f"Cycle time ({open_df.loc[idx, 'cycle_time']} days) exceeds threshold ({max_cycle})",
            ))

    # Split open issues based on errors
    if errors:
        error_indices = {e[0] for e in errors}
        valid_open_df = open_df[~open_df.index.isin(error_indices)].copy()

        # Build quality DataFrame with error info
        quality_rows = []
        for idx, error_code, message in errors:
            row = open_df.loc[idx].to_dict()
            row["error_code"] = error_code
            row["error_message"] = message
            quality_rows.append(row)

        quality_df = pd.DataFrame(quality_rows)
    else:
        valid_open_df = open_df.copy()
        quality_df = pd.DataFrame()

    # Merge validated open issues with closed issues (which skip validation)
    if not closed_df.empty:
        valid_df = pd.concat([valid_open_df, closed_df], ignore_index=True)
    else:
        valid_df = valid_open_df

    logger.info(f"Validation: {len(valid_df)} valid ({len(closed_df)} closed skipped), {len(quality_df)} failed")
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
