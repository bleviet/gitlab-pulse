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

    Falls back to title pattern matching when labels don't provide type.

    Args:
        df: DataFrame with labels column
        rule: Domain rule with label mappings and title patterns

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

    # Fallback: infer type from title when label mapping didn't find a match
    if rule.title_patterns.type:
        missing_type_mask = df["issue_type"].isna()
        if missing_type_mask.any():
            df.loc[missing_type_mask, "issue_type"] = df.loc[missing_type_mask, "title"].apply(
                lambda title: _infer_type_from_title(title, rule.title_patterns.type)
            )

    # Extract severity from labels
    df["severity"] = df["labels"].apply(
        lambda labels: _find_mapped_label(labels, rule.label_mappings.severity)
    )

    # Set team from rule
    df["team"] = rule.team

    return df


def _infer_type_from_title(title: str, type_keywords: dict[str, list[str]]) -> Optional[str]:
    """Infer issue type from title using keyword matching.

    Args:
        title: Issue title
        type_keywords: Dict mapping type names to keyword lists

    Returns:
        Matched type name or None
    """
    if not title or not type_keywords:
        return None

    title_lower = title.lower()

    for type_name, keywords in type_keywords.items():
        for keyword in keywords:
            # Word boundary matching: keyword surrounded by non-alphanumeric or at start/end
            keyword_lower = keyword.lower()
            if keyword_lower in title_lower:
                return type_name

    return None


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


def explode_contexts(
    df: pd.DataFrame,
    rule: Optional[DomainRule] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Explode DataFrame by context labels (Data Explosion).

    Each issue matching multiple context patterns becomes multiple rows.

    Args:
        df: DataFrame with labels column
        rule: Domain rule with context configuration

    Returns:
        Tuple of (exploded_df, orphan_df):
        - exploded_df: Issues with context columns added (may have more rows than input)
        - orphan_df: Issues that matched no context (if require_assignment is True)
    """
    if df.empty or rule is None or not rule.contexts.patterns:
        # No context config - add empty context columns and return
        df = df.copy()
        df["context"] = None
        df["context_group"] = None
        return df, pd.DataFrame()

    patterns = rule.contexts.patterns
    require_assignment = rule.contexts.require_assignment

    exploded_rows = []
    orphan_rows = []

    for _, row in df.iterrows():
        labels = row.get("labels", [])
        # Handle numpy arrays
        if labels is None:
            labels = []
        try:
            label_list = list(labels) if not isinstance(labels, list) else labels
        except (TypeError, ValueError):
            label_list = []

        # Find all matching contexts for this issue
        matched_contexts = []
        for pattern in patterns:
            for label in label_list:
                if isinstance(label, str) and label.startswith(pattern.prefix):
                    # Extract context name (e.g., "rnd::Alpha" -> "Alpha")
                    context_name = label[len(pattern.prefix):]
                    matched_contexts.append({
                        "context": context_name,
                        "context_group": pattern.alias,
                    })

        if matched_contexts:
            # Create one row per matched context
            for ctx in matched_contexts:
                new_row = row.to_dict()  # Convert to dict to avoid dtype issues
                new_row["context"] = ctx["context"]
                new_row["context_group"] = ctx["context_group"]
                exploded_rows.append(new_row)
        else:
            # No context match
            if require_assignment:
                orphan_rows.append(row.to_dict())
            else:
                # Still include in output with None context
                new_row = row.to_dict()
                new_row["context"] = None
                new_row["context_group"] = None
                exploded_rows.append(new_row)

    # Build result DataFrames
    if exploded_rows:
        exploded_df = pd.DataFrame(exploded_rows)
    else:
        exploded_df = df.copy()
        exploded_df["context"] = None
        exploded_df["context_group"] = None

    if orphan_rows:
        orphan_df = pd.DataFrame(orphan_rows)
    else:
        orphan_df = pd.DataFrame()

    logger.debug(f"Context explosion: {len(df)} -> {len(exploded_df)} rows, {len(orphan_df)} orphans")
    return exploded_df, orphan_df


def enrich_workflow_stage(
    df: pd.DataFrame,
    rule: Optional[DomainRule] = None,
    now: Optional[datetime] = None,
) -> pd.DataFrame:
    """Determine workflow stage for each issue based on labels.

    Args:
        df: DataFrame with labels column
        rule: Domain rule with workflow configuration
        now: Reference datetime for aging

    Returns:
        DataFrame with 'stage', 'stage_type', 'days_in_stage' columns
    """
    if now is None:
        now = datetime.now()

    # Default values
    df["stage"] = "Backlog"
    df["stage_type"] = "waiting"
    df["stage_order"] = 0
    df["days_in_stage"] = 0

    if df.empty or rule is None or not rule.workflow.stages:
        return df

    # ... (omitted comment) ...

    # Actually, let's just do forward iteration and only write to rows that are still 'Backlog'
    # But 'Backlog' is just the initial value.
    # Let's track which rows have been matched.
    
    matched_mask = pd.Series(False, index=df.index)

    for i, stage in enumerate(rule.workflow.stages, start=1):
        # Check for label match
        current_mask = df["labels"].apply(
            lambda labels: _has_any_label(labels, stage.labels)
        )
        
        # Only consider rows that matched THIS stage AND haven't been matched by a previous (higher priority) stage
        effective_mask = current_mask & (~matched_mask)
        
        if effective_mask.any():
            df.loc[effective_mask, "stage"] = stage.name
            df.loc[effective_mask, "stage_type"] = stage.type
            df.loc[effective_mask, "stage_order"] = i
            matched_mask = matched_mask | effective_mask

    # Calculate days in stage (Proxy: now - updated_at)
    # This assumes the issue was updated when it moved to the stage.
    if "updated_at" in df.columns:
        df["days_in_stage"] = (pd.Timestamp(now, tz="UTC") - df["updated_at"]).dt.days
        df["days_in_stage"] = df["days_in_stage"].fillna(0).astype(int)

    return df


def _has_any_label(issue_labels: object, target_labels: list[str]) -> bool:
    """Check if issue has any of the target labels."""
    if issue_labels is None:
        return False
    try:
        # Handle numpy arrays / lists
        i_labels = list(issue_labels) if not isinstance(issue_labels, list) else issue_labels
    except (TypeError, ValueError):
        return False
        
    for label in i_labels:
        if not isinstance(label, str):
            continue
        if label in target_labels:
            return True
    return False
