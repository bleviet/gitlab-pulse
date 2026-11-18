"""Tests for the clickable priority donut.

Plotly reports no click selection for pie slices, so the donut is drawn on x/y
axes with invisible click targets (see ``priority_donut``).
"""

import importlib
import math
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


def _render_closed(
    monkeypatch: pytest.MonkeyPatch, counts: dict[str | None, int], height: int
) -> go.Figure:
    captured: dict[str, go.Figure] = {}
    monkeypatch.setattr(
        widget.st, "plotly_chart", lambda fig, **_: captured.update(fig=fig)
    )
    ranks = {"P1": 1, "P2": 2, "P3": 3, None: None}
    priorities = [key for key, count in counts.items() for _ in range(count)]
    df = pd.DataFrame(
        {
            "state": ["closed"] * len(priorities),
            "priority": priorities,
            "priority_rank": [ranks[key] for key in priorities],
        }
    )
    config = {"height": height, "state_filter": "closed", "show_legend": False}
    widget.priority_donut(df, config)
    return captured["fig"]


@pytest.mark.parametrize("height", [150, 250])
def test_slice_values_stay_inside_their_ring_segment(
    monkeypatch: pytest.MonkeyPatch, height: int
) -> None:
    """Every drawn value fits the ring and its slice, at any chart height."""
    counts = {"P1": 563, "P2": 471, "P3": 679, None: 2434}
    fig = _render_closed(monkeypatch, counts, height)
    text_trace = next(trace for trace in fig.data if trace.mode == "text")

    total = sum(counts.values())
    slices: dict[str, tuple[float, float]] = {}
    start = 0.0
    for count in counts.values():
        slices[str(count)] = (start, 360.0 * count / total)
        start += 360.0 * count / total

    px_per_unit = (height - 20) / 2.16
    outer = px_per_unit
    inner = 0.6 * outer
    sizes = (
        text_trace.textfont.size
        if not isinstance(text_trace.textfont.size, int)
        else [text_trace.textfont.size] * len(text_trace.text)
    )
    shown = {}
    for text, size, x, y in zip(
        text_trace.text, sizes, text_trace.x, text_trace.y, strict=True
    ):
        if not text:
            continue
        shown[text] = size
        cx, cy = x * px_per_unit, y * px_per_unit
        half_w, half_h = 0.3 * size * len(text), 0.6 * size
        nearest = math.hypot(
            max(abs(cx) - half_w, 0.0), max(abs(cy) - half_h, 0.0)
        )
        assert nearest >= inner, text
        slice_start, sweep = slices[text]
        middle = slice_start + sweep / 2
        for dx in (-half_w, half_w):
            for dy in (-half_h, half_h):
                px, py = cx + dx, cy + dy
                assert math.hypot(px, py) <= outer, text
                angle = math.degrees(math.atan2(px, py))
                offset = (angle - middle + 180) % 360 - 180
                assert abs(offset) <= sweep / 2, text

    assert set(shown) == {"563", "471", "679", "2434"}
    if height == 150:
        assert shown["2434"] == 12


def test_single_priority_donut_shows_its_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A slice covering the whole ring still shows its value."""
    fig = _render_closed(monkeypatch, {"P1": 7}, 150)
    text_trace = next(trace for trace in fig.data if trace.mode == "text")

    assert list(text_trace.text) == ["7"]
