"""Paging for the issue table and the board: 10, 20 or 30 per page.

A bar above the table or the board, pinned below the toolbar while the page
scrolls, holds the size control and, when there is more than one page, the
previous/next buttons. The table and the lanes are as tall as one page, with
no scrolling inside: the page scrolls instead.

- **Table**: rows per page; the bar shows "11–20 of 408".
- **Board**: cards per lane. The pager turns all lanes together ("Page 2 of
  11"); a lane with fewer cards is empty on later pages.

Each view keeps its own size and page in session state
(``issue_<view>_rows``, ``issue_<view>_page``).
"""

from dataclasses import dataclass
from typing import Literal

import streamlit as st

View = Literal["table", "board"]

_SIZE_OPTIONS = ("10", "20", "30")
_DEFAULT_SIZE: dict[View, str] = {"table": "10", "board": "10"}
_SIZE_LABEL: dict[View, str] = {"table": "Rows", "board": "Cards per lane"}


@dataclass(frozen=True)
class PageWindow:
    """The slice of rows (table) or of each lane's cards (board) to show."""

    start: int
    stop: int


def page_bounds(total: int, size_option: str, page: int) -> tuple[int, int, int]:
    """Return ``(start, stop, page)`` for a size option, with the page clamped.

    Args:
        total: Number of rows (table) or cards in the longest lane (board).
        size_option: One of "10", "20", "30".
        page: Requested page, zero-based.
    """
    size = int(size_option)
    last_page = max((total - 1) // size, 0)
    page = min(max(page, 0), last_page)
    return page * size, min(total, (page + 1) * size), page


def _turn_page(view: View, step: int) -> None:
    key = f"issue_{view}_page"
    st.session_state[key] = st.session_state.get(key, 0) + step


def _change_size(view: View) -> None:
    # Clicking the active option deselects it; keep the current one then.
    choice = st.session_state.get(f"issue_{view}_rows_choice")
    if choice:
        st.session_state[f"issue_{view}_rows"] = choice
    st.session_state[f"issue_{view}_page"] = 0


def _pager_label(view: View, start: int, stop: int, total: int, size: int) -> str:
    if view == "board":
        return f"Page {start // size + 1} of {(total - 1) // size + 1}"
    return f"{start + 1}–{stop} of {total}"


def render_page_bar(view: View, total: int) -> PageWindow:
    """Render the size control (and page buttons) above the table or board.

    Args:
        view: "table" or "board".
        total: Number of rows (table) or cards in the longest lane (board).

    Returns:
        The slice to show.
    """
    size_key = f"issue_{view}_rows"
    page_key = f"issue_{view}_page"
    size_option = str(st.session_state.get(size_key, _DEFAULT_SIZE[view]))
    if size_option not in _SIZE_OPTIONS:
        size_option = _DEFAULT_SIZE[view]
    start, stop, page = page_bounds(total, size_option, int(st.session_state.get(page_key, 0)))
    st.session_state[page_key] = page
    st.session_state[f"issue_{view}_rows_choice"] = size_option
    with st.container(
        key="issue_page_bar",
        horizontal=True,
        horizontal_alignment="right",
        vertical_alignment="center",
    ):
        if total > int(size_option):
            st.button(
                "",
                icon=":material/chevron_left:",
                key=f"issue_{view}_prev",
                disabled=start == 0,
                on_click=_turn_page,
                args=(view, -1),
                help="Previous page",
            )
            st.caption(_pager_label(view, start, stop, total, int(size_option)))
            st.button(
                "",
                icon=":material/chevron_right:",
                key=f"issue_{view}_next",
                disabled=stop >= total,
                on_click=_turn_page,
                args=(view, 1),
                help="Next page",
            )
        st.caption(_SIZE_LABEL[view])
        st.segmented_control(
            _SIZE_LABEL[view],
            _SIZE_OPTIONS,
            key=f"issue_{view}_rows_choice",
            label_visibility="collapsed",
            on_change=_change_size,
            args=(view,),
        )
    return PageWindow(start, stop)
