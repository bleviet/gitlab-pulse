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


def _undated_issues() -> pd.DataFrame:
    now = pd.Timestamp.now(tz="UTC").normalize()
    return pd.DataFrame(
        {
            "id": list(range(1, 7)),
            "state": ["opened", "opened", "opened", "opened", "closed", "opened"],
            "milestone": ["dated", "v2.4.10", "v2.4.9", "v2.4.11", "old", "v2.4.2"],
            "milestone_id": [21, 22, 23, 24, 25, 26],
            "milestone_due_date": [
                now + pd.Timedelta(days=200),
                pd.NaT,
                pd.NaT,
                pd.NaT,
                pd.NaT,
                pd.NaT,
            ],
        }
    )


def _render(
    monkeypatch: pytest.MonkeyPatch, issues: pd.DataFrame, style: str
) -> go.Figure:
    captured: dict[str, go.Figure] = {}

    def fake_plotly_chart(fig: go.Figure, **_: Any) -> None:
        captured["fig"] = fig

    monkeypatch.setattr(widget.st, "plotly_chart", fake_plotly_chart)
    widget.milestone_timeline(issues, {"style": style, "height": 160})
    return captured["fig"]


def _points(fig: go.Figure) -> dict[str, tuple[Any, str, str]]:
    return {
        title: (x, trace.name, custom[0])
        for trace in fig.data
        for title, x, custom in zip(trace.text, trace.x, trace.customdata, strict=True)
    }


@pytest.mark.parametrize("style", ["default", "rail"])
def test_undated_active_milestones_are_unscheduled(
    monkeypatch: pytest.MonkeyPatch, style: str
) -> None:
    points = _points(_render(monkeypatch, _undated_issues(), style))
    assert points["v2.4.9"][1:] == ("Unscheduled", "Not set")
    assert "old" not in points


@pytest.mark.parametrize("style", ["default", "rail"])
def test_undated_section_follows_dated_and_range_covers_it(
    monkeypatch: pytest.MonkeyPatch, style: str
) -> None:
    fig = _render(monkeypatch, _undated_issues(), style)
    points = _points(fig)
    dated = pd.to_datetime(points["dated"][0], utc=True)
    undated = [pd.to_datetime(points[t][0], utc=True) for t in ("v2.4.2", "v2.4.9", "v2.4.10", "v2.4.11")]
    assert all(d > dated for d in undated)
    assert undated == sorted(undated)
    assert pd.Timestamp(fig.layout.xaxis.range[1], tz="UTC") > undated[-1]


@pytest.mark.parametrize("style", ["default", "rail"])
def test_undated_milestones_use_natural_version_order(
    monkeypatch: pytest.MonkeyPatch, style: str
) -> None:
    points = _points(_render(monkeypatch, _undated_issues(), style))
    xs = [pd.to_datetime(points[t][0], utc=True) for t in ("v2.4.9", "v2.4.10", "v2.4.11")]
    assert xs[0] < xs[1] < xs[2]


@pytest.mark.parametrize("style", ["default", "rail"])
def test_only_undated_milestones_still_render(
    monkeypatch: pytest.MonkeyPatch, style: str
) -> None:
    issues = _undated_issues().iloc[1:4]
    points = _points(_render(monkeypatch, issues, style))
    assert set(points) == {"v2.4.10", "v2.4.9", "v2.4.11"}


@pytest.mark.parametrize("style", ["default", "rail"])
def test_no_due_date_label_only_with_undated(
    monkeypatch: pytest.MonkeyPatch, style: str
) -> None:
    fig = _render(monkeypatch, _undated_issues(), style)
    assert any("No due date" in a.text for a in fig.layout.annotations)
    dated_only = _undated_issues().iloc[[0]]
    fig = _render(monkeypatch, dated_only, style)
    assert not any("No due date" in a.text for a in fig.layout.annotations)
