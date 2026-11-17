"""A second click on the Analytics chart segment that set the board's filter
removes the filter again (Analytics shows no filter chips)."""

import contextlib
import importlib
from types import SimpleNamespace
from typing import Any

import pytest

panel = importlib.import_module("app.dashboard.views.issue_panel")


class _Rerun(Exception):
    """Stands in for ``st.rerun``, which stops the script run."""


@pytest.fixture
def state(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    session: dict[str, Any] = {}

    def rerun() -> None:
        raise _Rerun

    monkeypatch.setattr(panel, "st", SimpleNamespace(session_state=session, rerun=rerun))
    return session


def _run(selection_points: list[dict[str, Any]], chart_id: str, **filters: str) -> None:
    """One script run in which the chart reports this selection."""
    with contextlib.suppress(_Rerun):
        panel.apply_chart_selection(
            {"selection": {"points": selection_points}}, chart_id, **filters
        )


def test_deselecting_a_bar_removes_its_filter(state: dict[str, Any]) -> None:
    """Plotly keeps a bar's selection, so the second click deselects it."""
    bar = [{"x": "P1", "y": 21}]
    _run(bar, "stage_bar_1", stage_filter="Architecture", state_filter="opened")
    _run(bar, "stage_bar_1", stage_filter="Architecture", state_filter="opened")
    assert state["issue_facets"] == {"stage": "Architecture", "state": "opened", "priority": "P1"}

    _run([], "stage_bar_1", stage_filter="Architecture", state_filter="opened")

    assert state["issue_facets"] == {}


def test_second_click_on_a_donut_slice_removes_its_filter(state: dict[str, Any]) -> None:
    """The donut redraws its highlight, which empties Plotly's selection, so
    the second click on the slice arrives as a new selection."""
    slice_ = [{"x": 0.3, "y": 0.6, "customdata": ["P1", 83]}]
    _run(slice_, "open_donut", state_filter="opened")
    _run([], "open_donut", state_filter="opened")
    assert state["issue_facets"] == {"state": "opened", "priority": "P1"}

    _run(slice_, "open_donut", state_filter="opened")

    assert state["issue_facets"] == {}


def test_search_text_survives_removing_a_chart_filter(state: dict[str, Any]) -> None:
    state["issue_facets"] = {"query": "crash"}
    slice_ = [{"customdata": ["P2", 76]}]
    _run(slice_, "open_donut", state_filter="opened")
    _run([], "open_donut", state_filter="opened")

    _run(slice_, "open_donut", state_filter="opened")

    assert state["issue_facets"] == {"query": "crash"}


def test_a_chart_reset_by_another_filter_does_not_clear_it(state: dict[str, Any]) -> None:
    """A chart rebuilt because the filter changed elsewhere reports an empty
    selection; that must not remove the new filter."""
    bar = [{"x": "P1", "y": 21}]
    _run(bar, "stage_bar_1", stage_filter="Architecture", state_filter="opened")
    _run(bar, "stage_bar_1", stage_filter="Architecture", state_filter="opened")
    panel._set_facets({"state": "closed"})

    _run([], "stage_bar_1", stage_filter="Architecture", state_filter="opened")

    assert state["issue_facets"] == {"state": "closed"}
