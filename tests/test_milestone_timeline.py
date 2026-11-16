"""Tests for the release timeline in rail style."""

import importlib
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import pytest

widget = importlib.import_module("app.dashboard.widgets.charts.milestone_timeline")


def _issues() -> pd.DataFrame:
    now = pd.Timestamp.now(tz="UTC").normalize()
    return pd.DataFrame(
        {
            "id": [1, 2, 3],
            "state": ["opened", "closed", "opened"],
            "milestone": ["v1.1", "v1.2", "v1.3"],
            "milestone_id": [11, 12, 13],
            "milestone_due_date": [
                now - pd.Timedelta(days=40),
                now - pd.Timedelta(days=40),
                now + pd.Timedelta(days=20),
            ],
        }
    )


@pytest.fixture
def rail_figure(monkeypatch: pytest.MonkeyPatch) -> go.Figure:
    captured: dict[str, go.Figure] = {}

    def fake_plotly_chart(fig: go.Figure, **_: Any) -> None:
        captured["fig"] = fig

    monkeypatch.setattr(widget.st, "plotly_chart", fake_plotly_chart)
    widget.milestone_timeline(_issues(), {"style": "rail", "height": 104})
    return captured["fig"]


def test_rail_alternates_milestones_above_and_below(rail_figure: go.Figure) -> None:
    """Round markers alternate sides of the rail, in date order."""
    assert rail_figure.layout.xaxis.type == "date"
    assert rail_figure.layout.height == 104
    positions = {
        title: y for trace in rail_figure.data for title, y in zip(trace.text, trace.y, strict=True)
    }
    assert positions == {"v1.1": 0.5, "v1.2": -0.5, "v1.3": 0.5}
    assert all(trace.marker.symbol == "circle" for trace in rail_figure.data)


def test_rail_marks_now(rail_figure: go.Figure) -> None:
    """A vertical line and a NOW label mark today's date."""
    today = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
    now_lines = [
        shape for shape in rail_figure.layout.shapes
        if shape.type == "line" and shape.x0 == today
    ]
    assert len(now_lines) == 1
    assert any("NOW" in annotation.text for annotation in rail_figure.layout.annotations)
