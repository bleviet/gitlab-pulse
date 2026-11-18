"""Board and table of the issue panel show the same issues (GitHub issue 7)."""

from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from typing import Any, cast

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

    def table(rows: pd.DataFrame, _facets: Any, page: PageWindow) -> None:
        seen["table_ids"] = rows["id"].tolist()
        seen["table_page"] = page

    seen["page_bars"] = []
    seen["window"] = PageWindow(0, 50)

    def page_bar(view: str, total: int) -> PageWindow:
        seen["page_bars"].append((view, total))
        return cast(PageWindow, seen["window"])

    def lane_header(_facets: Any, lane_counts: Any, _colors: Any) -> None:
        seen["lane_counts"] = lane_counts

    monkeypatch.setattr(issue_panel, "_render_toolbar", toolbar)
    monkeypatch.setattr(issue_panel, "_render_filter_chips", chips)
    monkeypatch.setattr(issue_panel, "render_page_bar", page_bar)
    monkeypatch.setattr(issue_panel.tables, "issue_board", board)
    monkeypatch.setattr(issue_panel, "render_issue_table", table)
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
    assert captured["page_bars"] == [("board", 0)]


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


def test_table_renders_the_page_bar_once_and_shows_its_window(
    captured: dict[str, Any],
) -> None:
    captured["view"] = "Table"
    captured["window"] = PageWindow(10, 20)

    issue_panel.render_issue_panel(_issues(), STAGES)

    assert captured["page_bars"] == [("table", 1)]
    assert captured["table_page"] == PageWindow(10, 20)


def test_board_renders_the_page_bar_once_and_shows_its_window(
    captured: dict[str, Any],
) -> None:
    captured["window"] = PageWindow(10, 20)

    issue_panel.render_issue_panel(_issues(), STAGES)

    assert captured["page_bars"] == [("board", 1)]
    config = captured["board_config"]
    assert config["card_start"] == 10
    assert config["max_cards"] == 10


def test_board_page_total_is_the_longest_lane(captured: dict[str, Any]) -> None:
    st.session_state["issue_facets"] = {"state": "opened"}

    issue_panel.render_issue_panel(_issues(), STAGES)

    assert captured["page_bars"] == [("board", 2)]


def test_table_without_matches_has_no_page_bar(captured: dict[str, Any]) -> None:
    captured["view"] = "Table"
    st.session_state["issue_facets"] = {"state": "opened", "query": "zzzz-no-match"}

    issue_panel.render_issue_panel(_issues(), STAGES)

    assert captured["page_bars"] == []
    assert "table_ids" not in captured


def test_board_without_matches_has_no_page_bar(captured: dict[str, Any]) -> None:
    st.session_state["issue_facets"] = {"state": "opened", "query": "zzzz-no-match"}

    issue_panel.render_issue_panel(_issues(), STAGES)

    assert captured["page_bars"] == []
    assert "board_ids" not in captured


@pytest.mark.parametrize("view", ["Table", "Board"])
def test_page_bar_row_is_in_the_head_before_the_body(
    captured: dict[str, Any], monkeypatch: pytest.MonkeyPatch, view: str
) -> None:
    events: list[str] = []
    stack: list[str] = []
    nesting: dict[str, list[str]] = {}
    stacks: dict[str, list[str]] = {}

    @contextmanager
    def container(*_a: Any, **k: Any) -> Iterator[None]:
        key = str(k.get("key"))
        nesting[key] = list(stack)
        events.append(f"enter {key}")
        stack.append(key)
        try:
            yield
        finally:
            stack.pop()

    def toolbar(_toolbar: Any) -> str:
        events.append("toolbar")
        return view

    def chips(_facets: Any, _caption: str) -> None:
        stacks["chips"] = list(stack)

    def page_bar(_view: str, _total: int) -> PageWindow:
        stacks["page_bar"] = list(stack)
        return PageWindow(0, 50)

    def table(rows: pd.DataFrame, _facets: Any, page: PageWindow) -> None:
        events.append("body")
        stacks["body"] = list(stack)

    def board(issues: pd.DataFrame, config: dict[str, Any]) -> None:
        events.append("body")
        stacks["body"] = list(stack)

    monkeypatch.setattr(st, "container", container)
    monkeypatch.setattr(issue_panel, "_render_toolbar", toolbar)
    monkeypatch.setattr(issue_panel, "_render_filter_chips", chips)
    monkeypatch.setattr(issue_panel, "render_page_bar", page_bar)
    monkeypatch.setattr(issue_panel, "render_issue_table", table)
    monkeypatch.setattr(issue_panel.tables, "issue_board", board)

    issue_panel.render_issue_panel(_issues(), STAGES)

    assert nesting["issue_panel_bar"] == ["issue_panel", "issue_panel_head"]
    assert stacks["chips"] == ["issue_panel", "issue_panel_head", "issue_panel_bar"]
    assert stacks["page_bar"] == ["issue_panel", "issue_panel_head", "issue_panel_bar"]
    if view == "Table":
        assert stacks["body"] == ["issue_panel"]
    else:
        assert stacks["body"][:1] == ["issue_panel"]
        assert "issue_panel_head" not in stacks["body"]
    assert (
        events.index("toolbar")
        < events.index("enter issue_panel_bar")
        < events.index("body")
    )
