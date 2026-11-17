"""Tests for rule-driven priority colours in the theme."""

import pytest

from app.dashboard import theme


@pytest.fixture(autouse=True)
def _isolated_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        theme, "_PRIORITY_PALETTE_KEYS", dict(theme._PRIORITY_PALETTE_KEYS)
    )


def test_registered_names_map_by_position() -> None:
    theme.register_priority_order(["High", "Medium", "Low", "Trivial"])
    palette = theme.get_palette()
    colors = theme.get_priority_colors()
    assert colors["High"] == palette["p1"]
    assert colors["Medium"] == palette["p2"]
    assert colors["Low"] == palette["p3"]
    assert colors["Trivial"] == palette["p3"]


def test_default_names_and_unset_still_map() -> None:
    theme.register_priority_order(["High", "Medium", "Low"])
    palette = theme.get_palette()
    colors = theme.get_priority_colors()
    assert colors["P1"] == palette["p1"]
    assert colors["Unset"] == palette["unset"]


def test_global_css_has_card_rule_for_registered_name() -> None:
    theme.register_priority_order(["High", "Medium", "Low"])
    css = theme.get_global_css()
    p1 = theme.get_palette()["p1"]
    assert f'[class*="-ibcard-high-"] {{ --ib-c: {p1}; }}' in css
