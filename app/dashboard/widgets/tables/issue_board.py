"""Issue Board Table Widget: read-only Kanban view grouped by workflow stage."""

import html
from collections.abc import Hashable, Mapping
from typing import Any

import pandas as pd
import streamlit as st

from app.dashboard.theme import priority_slug
from app.dashboard.utils import normalize_assignee_labels

_TITLE_MAX_CHARS = 70


def build_board_columns(
    df: pd.DataFrame, stages: list[str] | None = None
) -> list[tuple[str, pd.DataFrame]]:
    """Group issues into board columns, one per workflow stage.

    Each issue appears once, even if Layer 2 emitted several context rows for it.
    Columns follow the minimum ``stage_order`` of their stage (stage name if
    ``stage_order`` is missing). Cards are sorted by ``priority_rank`` ascending
    (missing last), then ``days_in_stage`` descending.

    Args:
        df: Analytics issues with at least ``stage`` and ``id`` columns.
        stages: Explicit columns, in display order. Columns without issues are
            kept (empty) so the board can line up with another grid; issues in
            other stages are left out.

    Returns:
        List of ``(stage, cards)`` tuples in display order. Without ``stages``,
        stages without issues are not included.
    """
    if df.empty or "stage" not in df.columns:
        return [(stage, df.iloc[0:0]) for stage in stages or []]

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

    if stages is None:
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
    """Build the card footer: assignee left, days in stage right."""
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
    return (
        f'<div class="ib-foot"><span class="ib-assignee">{html.escape(assignee)}'
        f'</span><span class="ib-right">{right}</span></div>'
    )


def _title_html(card: Mapping[Hashable, Any]) -> str:
    """Build the card title, a link to the issue when it has a ``web_url``."""
    title = html.escape(_truncate(str(card.get("title", ""))))
    url = card.get("web_url")
    if isinstance(url, str) and url:
        return (
            f'<a class="ib-title" href="{html.escape(url, quote=True)}" '
            f'target="_blank" rel="noopener">{title}</a>'
        )
    return f'<span class="ib-title">{title}</span>'


def _render_card(card: Mapping[Hashable, Any], key: str) -> None:
    """Render one issue card; its title opens the issue in a new tab."""
    slug = priority_slug(_priority_text(card))
    with st.container(key=f"{key}-ibcard-{slug}-{card.get('id')}"):
        st.markdown(_header_html(card), unsafe_allow_html=True)
        st.markdown(_title_html(card), unsafe_allow_html=True)
        st.markdown(_footer_html(card), unsafe_allow_html=True)


def issue_board(df: pd.DataFrame, config: dict[str, Any] | None = None) -> None:
    """Render a read-only Kanban board of issues grouped by stage.

    Args:
        df: Analytics issues (see ``build_board_columns``).
        config: Optional settings: ``key`` (widget key prefix, default
            ``"issue_board"``), ``lane_height`` (px, default 620; None: as
            tall as the cards, no scrolling inside), ``max_cards``
            (cards per column, default 50; None: all), ``card_start`` (first
            card shown in each column, for paging; default 0), ``stages``
            (explicit columns, see
            ``build_board_columns``), ``highlight_stage`` (column to mark),
            ``min_columns`` (grid width in columns, so a board with fewer
            columns keeps the same column width), ``lane_header`` (a
            callable ``(index, stage, cards)`` that renders a column's header
            instead of the default title and count) and ``lane_headers``
            (False: no column headers, for a page that shows the stages
            above the board; default True).
    """
    config = config or {}
    key = str(config.get("key", "issue_board"))
    max_cards = config.get("max_cards", 50)
    card_start = int(config.get("card_start", 0))
    lane_height = config.get("lane_height", 620)

    highlight_stage = config.get("highlight_stage")
    columns = build_board_columns(df, config.get("stages"))
    if not columns:
        st.info("No issues to display")
        return

    column_count = max(len(columns), int(config.get("min_columns", 0)))
    # The headers are a row of their own, not the top of each lane, so they can
    # stay pinned while the page scrolls: the lanes' row scrolls sideways on a
    # small screen, and nothing inside a sideways-scrolling row can stick to
    # the page (see the theme CSS and ``views.pinned_header``).
    head_slots: list[Any] = [None] * column_count
    if config.get("lane_headers", True):
        with st.container(key=f"{key}-ibheads"):
            head_slots = list(st.columns(column_count))
    slots = st.columns(column_count)
    for i, (head_slot, slot, (stage, cards)) in enumerate(
        zip(head_slots, slots, columns, strict=False)
    ):
        lane_kind = "iblane-hl" if stage == highlight_stage else "iblane"
        if head_slot is not None:
            with head_slot:
                lane_header = config.get("lane_header")
                if lane_header is not None:
                    lane_header(i, stage, cards)
                else:
                    st.markdown(
                        f'<div class="ib-lane-head{" ib-lane-hl" if lane_kind == "iblane-hl" else ""}">'
                        f"<b>{html.escape(stage)}</b> <small>{len(cards)}</small></div>",
                        unsafe_allow_html=True,
                    )
        with slot:
            with st.container(
                height="content" if lane_height is None else int(lane_height),
                border=False,
                key=f"{key}-{lane_kind}-{i}",
            ):
                shown = cards.iloc[card_start:] if max_cards is None else cards.iloc[
                    card_start:card_start + int(max_cards)
                ]
                if shown.empty:
                    st.caption("No issues" if cards.empty else "No more issues")
                for card in shown.to_dict("records"):
                    _render_card(card, key)
            remaining = len(cards) - card_start - len(shown)
            if remaining > 0:
                st.caption(f"+{remaining} more on the next pages")
