"""The figure cache: theme key and reuse of a builder's figure."""

import importlib

import pandas as pd
import plotly.graph_objects as go
import pytest

from app.dashboard import figure_cache

priority_bar = importlib.import_module("app.dashboard.widgets.charts.priority_bar")


def _counts() -> pd.DataFrame:
    return pd.DataFrame(
        {"Priority": ["P1", "P2"], "Count": [3, 1], "Rank": [1.0, 2.0], "IsUnset": [False, False]}
    )


def _build(
    highlight: str | None = None, theme_key: tuple[object, ...] = ("a",)
) -> go.Figure:
    return priority_bar._figure(
        _counts(), {"P1": "#111111", "P2": "#222222"}, highlight, False, 250, theme_key
    )


def test_theme_key_differs_between_light_and_dark(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(figure_cache, "get_active_theme_mode", lambda: "light")
    light = figure_cache.theme_key()
    monkeypatch.setattr(figure_cache, "get_active_theme_mode", lambda: "dark")

    assert figure_cache.theme_key() != light


def test_equal_arguments_return_the_same_figure() -> None:
    assert _build() is _build()


def test_highlight_gives_another_dimmed_figure() -> None:
    plain = _build()
    highlighted = _build("P1")

    assert highlighted is not plain
    opacities = {trace.name: trace.opacity for trace in highlighted.data}
    assert opacities == {"P1": 1.0, "P2": 0.2}


def test_theme_key_gives_another_figure() -> None:
    assert _build(theme_key=("b",)) is not _build()
