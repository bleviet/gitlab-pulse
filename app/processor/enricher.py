"""Vectorized metrics enrichment for Layer 2.

Calculates age_days, cycle_time, is_stale using Pandas vectorization.
"""

import logging
from datetime import datetime
from typing import Optional

import pandas as pd

from app.processor.rule_loader import DomainRule

logger = logging.getLogger(__name__)


def enrich_metrics(
    df: pd.DataFrame,
    rule: Optional[DomainRule] = None,
    now: Optional[datetime] = None,
) -> pd.DataFrame:
    """Enrich DataFrame with calculated metrics.

    Uses vectorized Pandas operations for high performance.

    Args:
        df: DataFrame with RawIssue columns
        rule: Domain rule for staleness threshold
        now: Reference datetime (default: current time)

    Returns:
        DataFrame with enriched columns (age_days, cycle_time, is_stale)
    """
    if df.empty:
        return df

    if now is None:
        now = datetime.now()

    stale_threshold = 30
    if rule:
        stale_threshold = rule.validation.stale_threshold_days

    # Ensure datetime columns are proper datetime types
    df = df.copy()
    for col in ["created_at", "updated_at", "closed_at"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], utc=True)

    # Age calculation (vectorized)
    df["age_days"] = (pd.Timestamp(now, tz="UTC") - df["created_at"]).dt.days

    # Cycle time calculation (vectorized, only for closed issues)
    df["cycle_time"] = pd.NA
    closed_mask = df["closed_at"].notna()
    if closed_mask.any():
        df.loc[closed_mask, "cycle_time"] = (
            df.loc[closed_mask, "closed_at"] - df.loc[closed_mask, "created_at"]
        ).dt.days

    # Staleness calculation (only for open issues)
    days_since_update = (pd.Timestamp(now, tz="UTC") - df["updated_at"]).dt.days
    df["is_stale"] = (df["state"] == "opened") & (days_since_update > stale_threshold)

    logger.debug(f"Enriched {len(df)} issues with metrics")
    return df


def apply_label_mappings(
    df: pd.DataFrame,
    rule: Optional[DomainRule] = None,
) -> pd.DataFrame:
    """Apply label mappings to extract issue_type, severity, etc.

    Args:
        df: DataFrame with labels column
        rule: Domain rule with label mappings

    Returns:
        DataFrame with issue_type, severity, team columns
    """
    if df.empty or rule is None:
        return df

    df = df.copy()

    # Extract issue type from labels
    df["issue_type"] = df["labels"].apply(
        lambda labels: _find_mapped_label(labels, rule.label_mappings.type)
    )

    # Extract severity from labels
    df["severity"] = df["labels"].apply(
        lambda labels: _find_mapped_label(labels, rule.label_mappings.severity)
    )

    # Set team from rule
    df["team"] = rule.team

    return df


def _find_mapped_label(labels: object, mapping: dict[str, str]) -> Optional[str]:
    """Find the first matching label in the mapping."""
    if labels is None or mapping is None:
        return None

    # Handle numpy arrays, lists, and other iterables
    try:
        label_list = list(labels) if not isinstance(labels, list) else labels
    except (TypeError, ValueError):
        return None

    if not label_list:
        return None

    for label in label_list:
        if not isinstance(label, str):
            continue
        # Exact match
        if label in mapping:
            return mapping[label]
        # Prefix match (e.g., "type::" matches "type::bug")
        for pattern, value in mapping.items():
            if label.startswith(pattern.rstrip("*")):
                return value

    return None
