"""Tests for the issue board column builder."""

import pandas as pd

from app.dashboard.theme import priority_slug
from app.dashboard.widgets.tables.issue_board import (
    _footer_html,
    _header_html,
    build_board_columns,
)


def _issues() -> pd.DataFrame:
    """Build issues across stages whose order differs from alphabetical."""
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5, 6],
            "stage": ["Review", "Backlog", "Review", "Review", "Review", "Backlog"],
            "stage_order": [2, 0, 2, 2, 2, 0],
            "priority_rank": [1.0, 0.0, None, 0.0, 1.0, 2.0],
            "days_in_stage": [3, 1, 9, 2, 7, 5],
        }
    )


def test_columns_follow_stage_order() -> None:
    """Columns are ordered by stage_order, not alphabetically."""
    result = build_board_columns(_issues().assign(stage_order=lambda d: 1 - d["stage_order"]))

    assert [stage for stage, _ in result] == ["Review", "Backlog"]


def test_duplicate_context_rows_yield_one_card() -> None:
    """Rows sharing an issue id collapse into a single card."""
    df = pd.concat([_issues(), _issues().iloc[[0]].assign(context="other")])

    cards = dict(build_board_columns(df))["Review"]

    assert cards["id"].is_unique
    assert len(cards) == 4


def test_cards_sorted_by_priority_then_days() -> None:
    """P1 precedes P2 precedes unset; ties are ordered by days_in_stage desc."""
    cards = dict(build_board_columns(_issues()))["Review"]

    assert cards["id"].tolist() == [4, 5, 1, 3]


def test_empty_stages_are_absent() -> None:
    """Only stages that contain issues become columns."""
    issues = _issues()
    df = issues[issues["stage"] == "Backlog"]

    assert [stage for stage, _ in build_board_columns(df)] == ["Backlog"]


def test_footer_omits_missing_days() -> None:
    """A missing days_in_stage does not raise or print 'nan'."""
    footer = _footer_html({"assignee": None, "days_in_stage": None})

    assert "nan" not in footer
    assert "ib-days" not in footer
    assert "Unassigned" in footer


def test_stale_class_only_when_is_stale_true() -> None:
    """Only is_stale=True gets the stale class and tooltip."""
    stale = _footer_html({"days_in_stage": 558, "is_stale": True})
    fresh = _footer_html({"days_in_stage": 5, "is_stale": False})

    assert "ib-stale" in stale and "558d" in stale
    assert "ib-stale" not in fresh and "Days in stage" in fresh


def test_link_only_for_non_empty_url() -> None:
    """The GitLab link is rendered, escaped, only when web_url is non-empty."""
    with_url = _footer_html({"web_url": "https://x/y?a=1&b=2"})

    assert 'href="https://x/y?a=1&amp;b=2"' in with_url
    assert "ib-link" not in _footer_html({"web_url": ""})
    assert "ib-link" not in _footer_html({"web_url": None})


def test_header_escapes_and_labels_priority() -> None:
    """Header shows iid and priority text (escaped); missing priority is Unset."""
    header = _header_html({"iid": 7, "priority": "<b>P1</b>"})

    assert "#7" in header
    assert "&lt;b&gt;P1&lt;/b&gt;" in header
    assert "Unset" in _header_html({"iid": 1, "priority": None})


def test_priority_slug() -> None:
    """Slugs are lowercase [a-z0-9]; unknown or empty names stay key-safe."""
    assert priority_slug("P1") == "p1"
    assert priority_slug("Very High!") == "veryhigh"
    assert priority_slug("!!!") == "unset"
