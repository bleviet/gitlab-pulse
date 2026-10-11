"""Issue Board Table Widget: read-only Kanban view grouped by workflow stage."""

import html
from collections.abc import Hashable, Mapping
from typing import Any

import pandas as pd
import streamlit as st

from app.dashboard.theme import priority_slug
from app.dashboard.utils import normalize_assignee_labels

_TITLE_MAX_CHARS = 70


def build_board_columns(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    """Group issues into board columns, one per workflow stage.

    Each issue appears once, even if Layer 2 emitted several context rows for it.
    Columns follow the minimum ``stage_order`` of their stage (stage name if
    ``stage_order`` is missing). Cards are sorted by ``priority_rank`` ascending
    (missing last), then ``days_in_stage`` descending.

    Args:
        df: Analytics issues with at least ``stage`` and ``id`` columns.

    Returns:
        List of ``(stage, cards)`` tuples in display order. Stages without
        issues are not included.
    """
    if df.empty or "stage" not in df.columns:
        return []

    issues = df.drop_duplicates(subset="id") if "id" in df.columns else df
    issues = issues.assign(
        _rank=pd.to_numeric(
            issues.get("priority_rank", pd.Series(pd.NA, index=issues.index)),
            errors="coerce",
        ),
        _days=pd.to_numeric(
            issues.get("days_in_stage", pd.Series(0, index=issues.index)),
            errors="coerce",
        ),
    ).sort_values(
        ["_rank", "_days"], ascending=[True, False], na_position="last", kind="stable"
    )
    issues = issues.assign(stage=issues["stage"].astype(str))

    if "stage_order" in issues.columns:
        order = issues.groupby("stage")["stage_order"].min().sort_values(kind="stable")
        stages = list(order.index)
    else:
        stages = sorted(issues["stage"].unique())

    cards = issues.drop(columns=["_rank", "_days"])
    return [(stage, cards[cards["stage"] == stage]) for stage in stages]


def _truncate(text: str, limit: int = _TITLE_MAX_CHARS) -> str:
    """Shorten text to ``limit`` characters, appending an ellipsis if cut."""
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _priority_text(card: Mapping[Hashable, Any]) -> str:
    """Return the card's priority name, or ``"Unset"`` when missing."""
    priority = card.get("priority")
    return "Unset" if pd.isna(priority) else str(priority)


def _header_html(card: Mapping[Hashable, Any]) -> str:
    """Build the card header: muted ``#iid`` and the priority chip."""
    priority = _priority_text(card)
    return (
        f'<div class="ib-head">#{html.escape(str(card.get("iid", "")))}'
        f'<span class="ib-chip ib-chip-{priority_slug(priority)}">'
        f"{html.escape(priority)}</span></div>"
    )


def _footer_html(card: Mapping[Hashable, Any]) -> str:
    """Build the card footer: assignee left; days and GitLab link right."""
    assignee = str(
        normalize_assignee_labels(pd.Series([card.get("assignee")])).iloc[0]
    )
    right = ""
    days = card.get("days_in_stage")
    if not pd.isna(days):
        if card.get("is_stale") is True:
            right += (
                f'<span class="ib-days ib-stale" '
                f'title="Stale: no recent update">{days:.0f}d</span>'
            )
        else:
            right += f'<span class="ib-days" title="Days in stage">{days:.0f}d</span>'
    url = card.get("web_url")
    if isinstance(url, str) and url:
        right += (
            f'<a class="ib-link" href="{html.escape(url, quote=True)}" '
            'target="_blank" rel="noopener" aria-label="Open in GitLab">↗</a>'
        )
    return (
        f'<div class="ib-foot"><span class="ib-assignee">{html.escape(assignee)}'
        f'</span><span class="ib-right">{right}</span></div>'
    )


def issue_board(df: pd.DataFrame, config: dict[str, Any] | None = None) -> str | None:
    """Render a read-only Kanban board of issues grouped by stage.

    Args:
        df: Analytics issues (see ``build_board_columns``).
        config: Optional settings: ``key`` (widget key prefix, default
            ``"issue_board"``), ``lane_height`` (px, default 620) and ``max_cards`` (cards per column, default 50).

    Returns:
        The ``web_url`` of the card clicked in this run, or None.
    """
    config = config or {}
    key = str(config.get("key", "issue_board"))
    max_cards = int(config.get("max_cards", 50))
    lane_height = int(config.get("lane_height", 620))

    columns = build_board_columns(df)
    if not columns:
        st.info("No issues to display")
        return None

    clicked: str | None = None
    slots = st.columns(len(columns))
    for i, (slot, (stage, cards)) in enumerate(zip(slots, columns, strict=True)):
        with slot:
            st.markdown(
                f"**{html.escape(stage)}** <small>({len(cards)})</small>",
                unsafe_allow_html=True,
            )
            with st.container(height=lane_height, border=False, key=f"{key}-iblane-{i}"):
                for card in cards.head(max_cards).to_dict("records"):
                    slug = priority_slug(_priority_text(card))
                    with st.container(key=f"{key}-ibcard-{slug}-{card.get('id')}"):
                        st.markdown(_header_html(card), unsafe_allow_html=True)
                        title = _truncate(str(card.get("title", "")))
                        if st.button(
                            title, key=f"{key}_{card.get('id')}", type="tertiary"
                        ):
                            url = card.get("web_url")
                            clicked = url if isinstance(url, str) and url else None
                        st.markdown(_footer_html(card), unsafe_allow_html=True)
            if len(cards) > max_cards:
                st.caption(f"+{len(cards) - max_cards} more in Table view")
    return clicked
