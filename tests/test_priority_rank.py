"""Tests for priority ranking and the overview priority selection mask."""

import pandas as pd

from app.dashboard.views.overview import _selection_mask_for_value
from app.processor.enricher import enrich_priority_rank
from app.processor.rule_loader import ClassificationMatch, DomainRule


def _rule(order: list[str]) -> DomainRule:
    """Build a rule whose priority classification follows the given order."""
    return DomainRule(
        classification={
            "priority": {
                name: ClassificationMatch(labels=[f"priority::{name}"])
                for name in order
            }
        }
    )


def _issues() -> pd.DataFrame:
    """Build issues with P1, P3, unset, and unknown priorities."""
    return pd.DataFrame(
        {
            "priority": ["P1", "P3", None, "P9"],
            "stage": ["Backlog"] * 4,
            "assignee": ["alice"] * 4,
            "state": ["opened"] * 4,
        }
    )


def test_priority_rank_follows_rule_order() -> None:
    """Known priorities get their 0-based position; others are NA."""
    result = enrich_priority_rank(_issues(), _rule(["P1", "P2", "P3"]))

    assert str(result["priority_rank"].dtype) == "Int64"
    assert result["priority_rank"].iloc[0] == 0
    assert result["priority_rank"].iloc[1] == 2
    assert pd.isna(result["priority_rank"].iloc[2])
    assert pd.isna(result["priority_rank"].iloc[3])


def test_priority_rank_respects_reversed_rule_order() -> None:
    """Reversing the YAML order reverses the ranks."""
    result = enrich_priority_rank(_issues(), _rule(["P3", "P2", "P1"]))

    assert result["priority_rank"].iloc[1] == 0
    assert result["priority_rank"].iloc[0] == 2


def test_priority_rank_without_priority_category_is_na() -> None:
    """A rule without a priority category yields only NA ranks."""
    rule = DomainRule(
        classification={"severity": {"High": ClassificationMatch(labels=["h"])}}
    )

    result = enrich_priority_rank(_issues(), rule)

    assert result["priority_rank"].isna().all()


def test_selection_mask_matches_priority_exactly() -> None:
    """A priority value selects only rows with that priority."""
    mask = _selection_mask_for_value(_issues(), "P1")

    assert mask.tolist() == [True, False, False, False]


def test_selection_mask_unset_matches_missing_priority() -> None:
    """The 'Unset' label selects rows without a priority."""
    mask = _selection_mask_for_value(_issues(), "Unset")

    assert mask.tolist() == [False, False, True, False]


def test_selection_mask_low_no_longer_matches_missing_priority() -> None:
    """Missing priorities are no longer relabeled as 'Low'."""
    mask = _selection_mask_for_value(_issues(), "Low")

    assert not mask.any()
