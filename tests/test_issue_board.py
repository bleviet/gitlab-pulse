"""Tests for the issue board column builder."""

from collections.abc import Hashable
from typing import Any

import pandas as pd

from app.dashboard.theme import priority_slug
from app.dashboard.widgets.tables.issue_board import (
    _footer_html,
    _header_html,
    _title_html,
    build_board_columns,
    priority_bar_html,
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


def test_footer_has_no_link() -> None:
    """The title is the link; the footer carries none."""
    assert "href" not in _footer_html({"web_url": "https://x/y", "days_in_stage": 3})


def test_title_links_to_escaped_url_in_new_tab() -> None:
    """The title is an escaped link that opens in a new tab."""
    title = _title_html({"title": "Fix <b>x</b>", "web_url": "https://x/y?a=1&b=2"})

    assert 'href="https://x/y?a=1&amp;b=2"' in title
    assert 'target="_blank"' in title
    assert 'rel="noopener"' in title
    assert "Fix &lt;b&gt;x&lt;/b&gt;" in title
    assert "<b>" not in title


def test_title_is_plain_without_url() -> None:
    """A card without a web_url shows its title without a link."""
    cards: list[dict[Hashable, Any]] = [
        {"title": "T", "web_url": ""},
        {"title": "T", "web_url": None},
        {"title": "T"},
    ]
    for card in cards:
        title = _title_html(card)
        assert "<a" not in title
        assert "ib-title" in title and ">T<" in title


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


def test_explicit_stages_keep_empty_columns_and_drop_other_stages() -> None:
    """Explicit columns line the board up with another grid."""
    columns = build_board_columns(_issues(), stages=["Triage", "Review"])

    assert [stage for stage, _ in columns] == ["Triage", "Review"]
    assert columns[0][1].empty
    assert columns[1][1]["id"].tolist() == [4, 5, 1, 3]


def test_explicit_stages_on_empty_issues_still_return_columns() -> None:
    """An empty board still has its columns, so lanes stay aligned."""
    columns = build_board_columns(_issues().iloc[0:0], stages=["Backlog", "Review"])

    assert [stage for stage, cards in columns if cards.empty] == ["Backlog", "Review"]


def test_priority_bar_html_has_one_segment_per_priority() -> None:
    assert "ib-pbar-empty" in priority_bar_html([])

    bar = priority_bar_html([("High", 3), ("Low", 1)])

    assert bar.count("<span") == 2
    assert "flex:3" in bar
    assert "flex:1" in bar
