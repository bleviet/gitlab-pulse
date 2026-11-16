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
