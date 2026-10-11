"""Tests for the Open vs. Closed issue state bar chart."""

import importlib
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import pytest

# The charts package re-exports the function under the module's name.
widget = importlib.import_module("app.dashboard.widgets.charts.issue_state_bar")


@pytest.fixture
def rendered_figure(monkeypatch: pytest.MonkeyPatch) -> go.Figure:
    """Render the widget and capture the Plotly figure passed to Streamlit."""
    captured: dict[str, go.Figure] = {}

    def fake_plotly_chart(fig: go.Figure, **_: Any) -> None:
        captured["fig"] = fig

    monkeypatch.setattr(widget.st, "plotly_chart", fake_plotly_chart)
    df = pd.DataFrame(
        {"id": [1, 2, 3], "state": ["opened", "closed", "closed"]}
    )
    widget.issue_state_bar(df)
    return captured["fig"]


def test_each_row_is_clickable_across_the_full_width(rendered_figure: go.Figure) -> None:
    """A click anywhere on a row, including its label, must hit a selectable bar.

    Plotly only reports a selection for clicks on a bar, so short bars left most
    of the row (label, count text, empty space) unclickable.
    """
    x_min, x_max = rendered_figure.layout.xaxis.range
    for state in ("opened", "closed"):
        covering = [
            trace
            for trace in rendered_figure.data
            for i, custom in enumerate(trace.customdata)
            if custom[0] == state
            and (trace.base if trace.base is not None else 0) <= x_min
            and (trace.base if trace.base is not None else 0) + trace.x[i]
            >= x_max - 1e-9
        ]
        assert covering, f"no full-width hit area for {state}"


def test_row_labels_are_drawn_inside_the_plot(rendered_figure: go.Figure) -> None:
    """Labels must sit inside the clickable plot area, not as axis tick labels."""
    labels = {annotation.text for annotation in rendered_figure.layout.annotations}
    assert labels == {"Open Issues", "Closed Issues"}
    assert rendered_figure.layout.yaxis.showticklabels is False
