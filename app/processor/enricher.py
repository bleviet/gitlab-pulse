"""Vectorized metrics enrichment for Layer 2.

Calculates age_days, cycle_time, is_stale using Pandas vectorization.
"""

import logging
from datetime import datetime
from typing import Optional

import pandas as pd

from app.processor.rule_loader import DomainRule
from app.processor.utils import has_any_label, match_text

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


def apply_classification(
    df: pd.DataFrame,
    rule: Optional[DomainRule] = None,
) -> pd.DataFrame:
    """Apply classification rules to extract attributes (type, severity, etc).

    Replaces legacy apply_label_mappings.
    """
    if df.empty or rule is None:
        return df

    df = df.copy()
    
    # 1. Ensure classification exists (migration logic handles legacy config)
    classification = rule.classification
    if not classification:
        return df

    # 2. Iterate over each category (e.g., "type", "severity", "priority")
    for category, values_map in classification.items():
        # Prepare target column
        # Standardize column naming if needed? For now matches category name.
        col_name = "issue_type" if category == "type" else category
        df[col_name] = None
        
        # We need to find the FIRST matching value for each row
        # Optimization: Iterate rows or iterate rules? 
        # Iterating rules is faster if number of rules < number of rows.
        
        # However, we need to respect priority (first match wins?). 
        # In a dict, order is insertion order (Python 3.7+). 
        # Assuming config order is priority.
        
        for value_name, match_rule in values_map.items():
            # Create a mask for rows that match THIS value rule
            # AND haven't been assigned a value yet
            
            # Check labels
            label_mask = df["labels"].apply(
                lambda labels: has_any_label(labels, match_rule.labels)
            )
            
            # Check title (only if checking 'type' or explicitly configured)
            # Legacy logic only inferred TYPE from title.
            # New logic: If title rules exist, check them.
            if match_rule.title:
                title_mask = df["title"].apply(
                    lambda title: any(match_text(title, t) for t in match_rule.title) if isinstance(title, str) else False
                )
                match_mask = label_mask | title_mask
            else:
                match_mask = label_mask
                
            # Assign value to rows that matched and are currently None
            current_missing = df[col_name].isna()
            effective_mask = match_mask & current_missing
            
            if effective_mask.any():
                df.loc[effective_mask, col_name] = value_name

    # Set team from rule (legacy behavior preserved)
    df["team"] = rule.team

    return df



def explode_contexts(
    df: pd.DataFrame,
    rule: Optional[DomainRule] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Explode DataFrame by context labels/titles (Data Explosion).

    Each issue matching multiple context rules becomes multiple rows.

    Args:
        df: DataFrame with labels and title columns
        rule: Domain rule with context configuration

    Returns:
        Tuple of (exploded_df, orphan_df):
        - exploded_df: Issues with context columns added (may have more rows than input)
        - orphan_df: Issues that matched no context (if require_assignment is True)
    """
    if df.empty or rule is None or not rule.contexts.rules:
        # No context config - add empty context columns and return
        df = df.copy()
        df["context"] = None
        df["context_group"] = None
        return df, pd.DataFrame()

    rules = rule.contexts.rules
    require_assignment = rule.contexts.require_assignment

    # Pre-compile regex patterns for performance if needed?
    # For now, simplistic implementation.

    exploded_rows = []
    orphan_rows = []

    for _, row in df.iterrows():
        # Prepare data for matching
        labels = row.get("labels", [])
        title = row.get("title", "")

        if labels is None:
            labels = []
        try:
            label_list = list(labels) if not isinstance(labels, list) else labels
        except (TypeError, ValueError):
            label_list = []

        # Ensure labels are strings
        label_list = [str(l) for l in label_list if l]

        # Find all keys/values for this issue
        matched_contexts = []

        for ctx_rule in rules:
            # check labels
            for pattern in ctx_rule.labels:
                for label in label_list:
                    match_val = _match_text(label, pattern)
                    if match_val:
                        matched_contexts.append({
                            "context": match_val if match_val is not True else label, # Use matched string or label
                            "context_group": ctx_rule.name,
                        })

            # check title
            for pattern in ctx_rule.title:
                if isinstance(title, str):
                    match_val = _match_text(title, pattern)
                    if match_val:
                         # For title matches, use rule name as context to avoid high cardinality
                        matched_contexts.append({
                            "context": ctx_rule.name,
                            "context_group": ctx_rule.name,
                        })

        # Deduplicate matches (same context and group)
        unique_matches = []
        seen = set()
        for m in matched_contexts:
            key = (m["context"], m["context_group"])
            if key not in seen:
                seen.add(key)
                unique_matches.append(m)

        if unique_matches:
            # Create one row per matched context
            for ctx in unique_matches:
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


def _match_text(text: str, pattern: str) -> Optional[str|bool]:
    """Check if text matches pattern.

    Returns:
        - None if no match
        - Matched String (for regex capture) or True (for simple match)
    """
    if pattern.startswith("regex:"):
        regex = pattern[6:]
        try:
            match = re.search(regex, text)
            if match:
                # Return the full match or the first group if present?
                # Let's match existing logic: return the full text that matched effectively?
                # Or just return True?
                # For context extracting, usually we want the specific label.
                return True
        except re.error:
            pass

    elif pattern.startswith("contains:"):
        substring = pattern[9:]
        if substring in text:
            return True

    elif pattern.startswith("exact:"):
        exact_str = pattern[6:]
        if text == exact_str:
            return True

    else:
        # Default to exact match
        if text == pattern:
            return True

    return None


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

    # Closed issues are always "Done" regardless of labels
    if "state" in df.columns:
        closed_mask = df["state"] == "closed"
        if closed_mask.any():
            df.loc[closed_mask, "stage"] = "Done"
            df.loc[closed_mask, "stage_type"] = "completed"
            # Done stage comes after all other stages
            max_order = df["stage_order"].max()
            df.loc[closed_mask, "stage_order"] = max_order + 1

    return df


import re

def _has_any_label(issue_labels: object, target_labels: list[str]) -> bool:
    """Check if issue has any of the target labels.

    Supports "regex:", "contains:", and "exact:" prefixes via _match_text.
    """
    if issue_labels is None:
        return False
    try:
        # Handle numpy arrays / lists
        i_labels = list(issue_labels) if not isinstance(issue_labels, list) else issue_labels
    except (TypeError, ValueError):
        return False

    for target in target_labels:
        # Optimization: Check for simple exact match first if no prefix
        is_simple = not (target.startswith("regex:") or target.startswith("contains:") or target.startswith("exact:"))
        
        for label in i_labels:
            if not isinstance(label, str):
                continue
            
            # Use unified matching logic
            if _match_text(label, target):
                 return True
                 
    return False
