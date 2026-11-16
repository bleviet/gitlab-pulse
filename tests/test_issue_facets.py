"""Tests for the Overview issue-list facets."""

import pandas as pd

from app.dashboard.views.issue_data import (
    board_lanes,
    collapse_issue_contexts,
    facet_chips,
    facets_from_query,
    facets_from_selection,
    facets_to_query,
    filter_issues,
    lane_priority_counts,
    overview_stages,
    priority_color_names,
    priority_labels,
    recent_mask,
    without_facet,
)


def _issues() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 1, 2, 3, 4],
            "iid": [1, 1, 2, 3, 4],
            "stage": ["Review", "Review", "Review", "Backlog", "Done"],
            "state": ["opened", "opened", "opened", "opened", "closed"],
            "priority": ["P1", "P1", "P2", None, "P1"],
            "assignee": ["ann", "ann", "bob", None, "ann"],
            "milestone": ["v1", "v1", None, "v1", "v1"],
            "labels": [["type::bug"]] * 5,
            "context": ["project::A", "project::B", None, "project::A", None],
            "created_at": pd.to_datetime(
                ["2026-11-01", "2026-11-01", "2026-11-02", "2026-11-02", "2026-10-01"],
                utc=True,
            ),
            "closed_at": pd.to_datetime(
                [None, None, None, None, "2026-11-02"], utc=True
            ),
        }
    )


def test_stage_and_priority_facets_filter_issues() -> None:
    """A lane pill (stage and priority) selects matching open issues."""
    facets = {"stage": "Review", "state": "opened", "priority": "P1"}

    assert filter_issues(_issues(), facets)["id"].unique().tolist() == [1]


def test_closed_priority_and_signal_facets() -> None:
    """State, priority and quality-signal facets combine."""
    assert filter_issues(_issues(), {"state": "closed", "priority": "P1"})["id"].tolist() == [4]
    signal = {"signal": "MISSING_MILESTONE"}
    assert filter_issues(_issues(), signal)["id"].tolist() == [2]


def test_unset_priority_facet_matches_missing_priority() -> None:
    """The "Unset" pill selects issues without a priority."""
    facets = {"state": "opened", "priority": "Unset"}

    assert filter_issues(_issues(), facets)["id"].tolist() == [3]


def test_chips_describe_facets_and_can_be_removed_one_by_one() -> None:
    """Each facet yields a chip, and removing one keeps the rest."""
    facets = {"stage": "Review", "priority": "P1"}

    assert facet_chips(facets) == [("stage", "Stage: Review"), ("priority", "Priority: P1")]
    assert without_facet(facets, "priority") == {"stage": "Review"}


def test_facets_round_trip_through_query_params_and_drop_bad_values() -> None:
    """URL parameters restore facets and ignore malformed ones."""
    facets = {"stage": "Review", "state": "closed", "recent": "closed", "query": "login"}

    assert facets_from_query(facets_to_query(facets)) == facets
    assert facets_from_query({"f_state": "deleted", "f_recent": "never", "other": "x"}) == {}


def test_collapse_issue_contexts_keeps_one_row_per_issue() -> None:
    """Issues emitted once per context should collapse into one row."""
    collapsed = collapse_issue_contexts(_issues())

    assert collapsed["id"].tolist() == [1, 2, 3, 4]
    assert collapsed["context"].tolist() == [
        ["project::A", "project::B"],
        [],
        ["project::A"],
        [],
    ]


def test_overview_stages_lists_stages_with_open_issues_in_workflow_order() -> None:
    """The workflow chart's stages are the stages that have open issues."""
    df = _issues().assign(stage_order=[2, 2, 2, 0, 9])

    assert overview_stages(df) == ["Backlog", "Review"]


def test_board_lanes_keep_chart_stages_and_append_other_stages() -> None:
    """Lanes line up with the chart and add stages the chart does not show."""
    df = _issues().assign(stage_order=[2, 2, 2, 0, 9])
    chart = ["Backlog", "Review"]

    review_only = df[df["stage"] == "Review"]
    assert board_lanes(chart, review_only) == ["Backlog", "Review"]
    assert board_lanes(chart, df) == ["Backlog", "Review", "Done"]
    assert board_lanes(chart, df[df["state"] == "closed"]) == ["Done"]


def test_query_facet_searches_issues_and_shows_a_chip() -> None:
    """Search text filters like any facet and survives the URL round trip."""
    df = _issues().assign(title=["Fix login", "Fix login", "Add export", "Login page", "Docs"])
    facets = {"query": "login"}

    assert filter_issues(df, facets)["id"].unique().tolist() == [1, 3]
    assert facet_chips(facets) == [("query", "Search: login")]
    assert facets_from_query(facets_to_query(facets)) == facets


def test_state_all_disables_the_state_filter_and_open_needs_no_chip() -> None:
    """Open issues are the default, so only Closed and All get a chip."""
    assert filter_issues(_issues(), {"state": "all"})["id"].unique().tolist() == [1, 2, 3, 4]
    assert facet_chips({"state": "all"}) == [("state", "State: All")]
    assert facet_chips({"state": "closed"}) == [("state", "State: Closed")]
    assert facet_chips({"state": "opened"}) == []


def test_recent_facet_keeps_issues_created_or_closed_in_the_last_week() -> None:
    """The 7-day window covers today and the six days before it."""
    now = pd.Timestamp("2026-11-16 10:00", tz="UTC")
    df = pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "state": ["opened", "closed", "closed", "opened"],
            "created_at": pd.to_datetime(
                ["2026-11-10", "2026-11-01", "2026-11-12", "2026-11-09"], utc=True
            ),
            "closed_at": pd.to_datetime([None, "2026-11-15", "2026-11-08", None], utc=True),
        }
    )

    assert recent_mask(df, "created", now).tolist() == [True, False, True, False]
    assert recent_mask(df, "closed", now).tolist() == [False, True, False, False]
    assert facet_chips({"state": "closed", "recent": "closed"}) == [
        ("recent", "Closed: last 7 days")
    ]
    assert facets_from_query({"f_recent": "someday"}) == {}


def test_priority_labels_and_lane_counts_follow_rank_with_unset_last() -> None:
    """Lane headers count issues per stage and priority, most urgent first."""
    df = _issues()

    assert priority_labels(df).tolist() == ["P1", "P1", "P2", "Unset", "P1"]
    counts = lane_priority_counts(df.drop_duplicates("id").assign(priority_rank=[1, 2, None, 1]))
    assert counts == {
        "Backlog": [("Unset", 1)],
        "Done": [("P1", 1)],
        "Review": [("P1", 1), ("P2", 1)],
    }


def test_priority_colours_follow_rank_and_unset_is_gray() -> None:
    """Summary pills and lane headers share one dot colour per priority."""
    df = _issues().assign(priority_rank=[1, 1, 2, None, 1])

    assert priority_color_names(df) == {"P1": "red", "P2": "orange", "Unset": "gray"}


def test_analytics_chart_selections_become_board_facets() -> None:
    """A click in an Analytics chart translates into the board's facets."""
    stage_bar = facets_from_selection(
        "stage_bar_2", [{"x": "P1"}], stage_filter="Review", state_filter="opened"
    )
    donut = facets_from_selection(
        "closed_donut", [{"customdata": ["P2", 76]}], state_filter="closed"
    )
    state = facets_from_selection(
        "issue_state_chart", [{"y": "Closed Issues", "customdata": ["closed"]}]
    )
    signal = facets_from_selection(
        "quality_signal_chart", [{"y": "Missing Milestone", "customdata": ["MISSING_MILESTONE"]}]
    )

    assert stage_bar == {"stage": "Review", "state": "opened", "priority": "P1"}
    assert donut == {"state": "closed", "priority": "P2"}
    assert state == {"state": "closed"}
    assert signal == {"signal": "MISSING_MILESTONE"}


def test_velocity_point_selects_the_issues_created_or_closed_that_day() -> None:
    """A velocity point becomes a day facet with the matching state."""
    created = facets_from_selection("velocity_chart", [{"x": "2026-11-02", "customdata": ["New"]}])
    closed = facets_from_selection("velocity_chart", [{"x": "2026-11-02", "curveNumber": 1}])

    assert created == {"state": "opened", "day": "2026-11-02", "day_kind": "created"}
    assert closed == {"state": "closed", "day": "2026-11-02", "day_kind": "closed"}
    assert filter_issues(_issues(), created)["id"].tolist() == [2, 3]
    assert filter_issues(_issues(), closed)["id"].tolist() == [4]
    assert facet_chips(closed) == [("day", "Closed: Nov 02, 2026")]
    assert without_facet(closed, "day") == {"state": "closed"}
    assert facets_from_query(facets_to_query(closed)) == closed
    assert facets_from_query({"f_day": "not-a-date", "f_day_kind": "closed"}) == {}


def test_donut_slice_and_centre_selections() -> None:
    """A slice selects its priority; the centre selects the whole state."""
    slice_ = facets_from_selection(
        "open_donut", [{"x": 0.3, "y": 0.6, "customdata": ["P1", 83]}], state_filter="opened"
    )
    centre = facets_from_selection(
        "closed_donut", [{"x": 0.0, "y": 0.0, "customdata": ["__all__", 592]}], state_filter="closed"
    )

    assert slice_ == {"state": "opened", "priority": "P1"}
    assert centre == {"state": "closed"}
