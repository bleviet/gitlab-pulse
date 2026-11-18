"""Tests for the clickable priority donut.

Plotly reports no click selection for pie slices, so the donut is drawn on x/y
axes with invisible click targets (see ``priority_donut``).
"""

import importlib
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import pytest

widget = importlib.import_module("app.dashboard.widgets.charts.priority_donut")


def _render(monkeypatch: pytest.MonkeyPatch, config: dict[str, Any]) -> go.Figure:
    captured: dict[str, go.Figure] = {}

    def fake_plotly_chart(fig: go.Figure, **_: Any) -> None:
        captured["fig"] = fig

    monkeypatch.setattr(widget.st, "plotly_chart", fake_plotly_chart)
    df = pd.DataFrame(
        {
            "state": ["opened"] * 4,
            "priority": ["P1", "P1", "P2", None],
            "priority_rank": [1, 1, 2, None],
        }
    )
    widget.priority_donut(df, config)
    return captured["fig"]


def test_no_pie_trace_and_every_slice_has_click_targets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Slices are scatter shapes; click targets carry the priority and count."""
    fig = _render(monkeypatch, {"show_legend": False})

    assert not any(trace.type == "pie" for trace in fig.data)
    targets = next(trace for trace in fig.data if trace.mode == "markers")
    labels = {tuple(item) for item in targets.customdata}
    assert labels == {("P1", 2), ("P2", 1), ("Unset", 1), (widget.ALL_ISSUES, 4)}


def test_highlight_dims_the_other_slices(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only the highlighted priority keeps its full colour."""
    fig = _render(monkeypatch, {"show_legend": False, "highlight": "P2"})

    fills = {trace.name: trace.fillcolor for trace in fig.data if trace.fill == "toself"}
    assert not fills["P2"].startswith("rgba")
    assert fills["P1"].startswith("rgba") and fills["Unset"].startswith("rgba")


@pytest.mark.parametrize("drop", ["priority_rank", "state"])
def test_donut_and_bar_render_without_optional_columns(
    monkeypatch: pytest.MonkeyPatch, drop: str
) -> None:
    """Missing ``priority_rank`` or ``state`` columns count all rows, no error."""
    bar = importlib.import_module("app.dashboard.widgets.charts.priority_bar")
    figures: list[go.Figure] = []
    monkeypatch.setattr(
        widget.st, "plotly_chart", lambda fig, **_: figures.append(fig)
    )
    df = pd.DataFrame(
        {
            "state": ["opened", "opened", "closed"],
            "priority": ["P1", "P1", "P2"],
            "priority_rank": [1, 1, 2],
        }
    ).drop(columns=[drop])

    widget.priority_donut(df, {"state_filter": "all", "show_legend": False})
    bar.priority_bar(df, {"show_all": True})

    assert len(figures) == 2
    donut_targets = next(t for t in figures[0].data if t.mode == "markers")
    assert {tuple(item) for item in donut_targets.customdata} == {
        ("P1", 2),
        ("P2", 1),
        (widget.ALL_ISSUES, 3),
    }
    assert sorted(int(v) for trace in figures[1].data for v in trace.y) == [1, 2]
