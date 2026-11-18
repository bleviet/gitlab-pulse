"""Board and table of the issue panel show the same issues (GitHub issue 7)."""

from contextlib import nullcontext
from typing import Any

import pandas as pd
import pytest
import streamlit as st

from app.dashboard.views import issue_panel
from app.dashboard.views.issue_data import facets_from_selection
from app.dashboard.views.issue_pages import PageWindow

STAGES = ["Backlog", "Implementation", "Testing"]


def _issues() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4],
            "iid": [1, 2, 3, 4],
            "title": ["a", "b", "c", "d"],
            "web_url": [f"https://x/{n}" for n in range(1, 5)],
            "stage": ["Backlog", "Implementation", "Implementation", "Testing"],
            "state": ["opened"] * 4,
            "priority": ["Medium", "Medium", "High", "Medium"],
            "priority_rank": [2, 2, 1, 2],
            "days_in_stage": [1, 2, 3, 4],
            "assignee": [None] * 4,
            "milestone": [None] * 4,
            "labels": [["type::bug"]] * 4,
            "context": [None] * 4,
        }
    )


@pytest.fixture
def captured(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Stub the rendering and record what the panel hands to it."""
    seen: dict[str, Any] = {"view": "Board"}
    facets = facets_from_selection(
        "stage_bar_1",
        [{"x": "Medium", "y": 2, "curveNumber": 0}],
        "Implementation",
        "opened",
    )
    monkeypatch.setattr(
        st,
        "session_state",
        {"issue_facets": facets, "filtered_issues_view": "Board"},
    )
    monkeypatch.setattr(st, "container", lambda *a, **k: nullcontext())

    def toolbar(_toolbar: Any) -> str:
        return str(seen["view"])

    def chips(_facets: Any, caption: str) -> None:
        seen["caption"] = caption

    def board(issues: pd.DataFrame, config: dict[str, Any]) -> None:
        seen["board_ids"] = issues["id"].tolist()
        seen["board_config"] = config

    def table(rows: pd.DataFrame, _facets: Any) -> None:
        seen["table_ids"] = rows["id"].tolist()

    def lane_header(_facets: Any, lane_counts: Any, _colors: Any) -> None:
        seen["lane_counts"] = lane_counts

    monkeypatch.setattr(issue_panel, "_render_toolbar", toolbar)
    monkeypatch.setattr(issue_panel, "_render_filter_chips", chips)
    monkeypatch.setattr(issue_panel, "render_page_bar", lambda *a, **k: range(50))
    monkeypatch.setattr(issue_panel.tables, "issue_board", board)
    monkeypatch.setattr(issue_panel, "_render_issue_table", table)
    monkeypatch.setattr(issue_panel, "_lane_header_renderer", lane_header)
    return seen


def test_board_applies_the_stage_scoped_priority(captured: dict[str, Any]) -> None:
    issue_panel.render_issue_panel(_issues(), STAGES)

    assert captured["board_ids"] == [2]
    assert captured["caption"] == "1 issue"


def test_board_keeps_all_lanes_and_marks_the_stage(captured: dict[str, Any]) -> None:
    issue_panel.render_issue_panel(_issues(), STAGES)

    config = captured["board_config"]
    assert config["stages"] == STAGES
    assert config["min_columns"] == len(STAGES)
    assert config["highlight_stage"] == "Implementation"


def test_lane_headers_keep_the_full_priority_mix(captured: dict[str, Any]) -> None:
    issue_panel.render_issue_panel(_issues(), STAGES)

    assert captured["lane_counts"] == {
        "Backlog": [("Medium", 1)],
        "Implementation": [("High", 1), ("Medium", 1)],
        "Testing": [("Medium", 1)],
    }


def test_table_shows_the_same_issue_and_caption(captured: dict[str, Any]) -> None:
    captured["view"] = "Table"
    st.session_state["filtered_issues_view"] = "Table"

    issue_panel.render_issue_panel(_issues(), STAGES)

    assert captured["table_ids"] == [2]
    assert captured["caption"] == "1 issue"


def test_board_keeps_lanes_when_the_full_facets_match_nothing(
    captured: dict[str, Any],
) -> None:
    st.session_state["issue_facets"] = {
        "stage": "Backlog",
        "priority": "High",
        "state": "opened",
    }

    issue_panel.render_issue_panel(_issues(), STAGES)

    assert captured["board_ids"] == []
    assert captured["board_config"]["stages"] == STAGES


def test_prepare_issue_rows_leaves_the_hints_to_the_page() -> None:
    rows = issue_panel._prepare_issue_rows(_issues())

    assert "quality_hints" not in rows.columns


def test_table_computes_hints_only_for_the_page(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []
    original = issue_panel._issue_quality_hints_text

    def counting(row: pd.Series) -> str:
        calls.append(1)
        return original(row)

    shown: dict[str, pd.DataFrame] = {}

    def grid(styler: Any, *_a: Any, **_k: Any) -> None:
        shown["frame"] = styler.data

    monkeypatch.setattr(issue_panel, "render_page_bar", lambda *a, **k: PageWindow(0, 2))
    monkeypatch.setattr(issue_panel, "load_labels", lambda: {})
    monkeypatch.setattr(issue_panel.tables, "issue_detail_grid", grid)
    monkeypatch.setattr(issue_panel, "_issue_quality_hints_text", counting)

    rows = issue_panel._prepare_issue_rows(_issues().assign(context=[[]] * 4))
    issue_panel._render_issue_table(rows, {})

    frame = shown["frame"]
    assert len(calls) == 2
    assert len(frame) == 2
    assert frame["quality_hints"].tolist() == [
        "Unassigned owner | Missing milestone"
    ] * 2
    assert frame["quality_hints"].tolist() == [
        original(row) for _, row in rows.iloc[0:2].iterrows()
    ]


def test_table_view_does_not_compute_lane_counts(
    captured: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    captured["view"] = "Table"

    def fail(*_a: Any, **_k: Any) -> None:
        raise AssertionError("lane counts computed in Table view")

    monkeypatch.setattr(issue_panel, "lane_priority_counts", fail)

    issue_panel.render_issue_panel(_issues(), STAGES)

    assert captured["table_ids"] == [2]


def test_resetting_a_sidebar_filter_requests_a_full_rerun(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state: dict[str, Any] = {"sidebar_team_selector": "Team A"}
    monkeypatch.setattr(st, "session_state", state)

    issue_panel._reset_sidebar_filter("sidebar_team_selector")

    assert state["sidebar_team_selector"] == "All"
    assert state[issue_panel.FULL_RERUN_KEY] is True


def test_typed_search_is_applied_in_the_same_run(
    captured: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    st.session_state["issue_facets"] = {"state": "opened"}
    captured["view"] = "Table"

    def toolbar(_toolbar: Any) -> str:
        issue_panel._set_search_query("2")
        return "Table"

    monkeypatch.setattr(issue_panel, "_render_toolbar", toolbar)

    issue_panel.render_issue_panel(_issues(), STAGES)

    assert captured["table_ids"] == [2]
    assert captured["caption"] == "1 issue"
