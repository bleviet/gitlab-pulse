"""Tests for the Overview summary pills."""

import pandas as pd

from app.dashboard.views.overview_summary import build_summary

NOW = pd.Timestamp("2026-11-16 10:00", tz="UTC")


def _issues() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "state": ["opened", "opened", "opened", "closed", "closed"],
            "priority": ["P1", "P2", None, "P1", "P2"],
            "priority_rank": [1, 2, None, 1, 2],
            "assignee": ["ann", None, "bob", "ann", "bob"],
            "milestone": ["v1", None, None, "v1", "v1"],
            "labels": [["type::bug"], ["type::bug", "type::feature"], [], [], []],
            "created_at": pd.to_datetime(
                ["2026-11-14", "2026-01-01", "2026-11-15", "2026-10-01", "2026-10-02"],
                utc=True,
            ),
            "closed_at": pd.to_datetime([None, None, None, "2026-11-13", "2026-10-03"], utc=True),
        }
    )


def test_flow_pills_count_states_and_the_last_week() -> None:
    """Flow pills count open issues and the 7-day activity."""
    flow = {item.item_id: item for item in dict(build_summary(_issues(), now=NOW))["Flow"]}

    assert flow["open"].value == 3
    assert "closed" not in flow
    assert flow["new_recent"].value == 2
    assert flow["closed_recent"].value == 1
    assert flow["closed_recent"].facets == {"state": "closed", "recent": "closed"}


def test_priority_pills_follow_rank_with_unset_last_and_coloured_dots() -> None:
    """Open issues per priority, the most urgent first, each with a dot."""
    priorities = dict(build_summary(_issues(), now=NOW))["Open by priority"]

    assert [(item.label, item.value) for item in priorities] == [("P1", 1), ("P2", 1), ("Unset", 1)]
    assert [item.color for item in priorities] == ["red", "orange", "gray"]
    assert priorities[0].pill_label() == ":red[●] P1 **1**"
    assert priorities[2].facets == {"state": "opened", "priority": "Unset"}


def test_hint_pills_count_open_issues_with_quality_signals() -> None:
    """Hints count open issues only; a pill shows an icon and the count."""
    hints = {item.label: item for item in dict(build_summary(_issues(), now=NOW))["Hints"]}

    assert hints["No milestone"].value == 2
    assert hints["Unassigned"].value == 1
    assert hints["Mixed"].value == 1
    assert hints["No milestone"].pill_label() == ":material/event_busy: No milestone **2**"
