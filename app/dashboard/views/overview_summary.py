"""Summary pills of the Overview page.

Counts that need no chart (open issues, issues opened and closed in the last
seven days, open issues per priority, quality hints) are shown as pills in the board's toolbar
row. Picking a pill sets the board's filter; picking it again resets it.
"""

from collections.abc import Callable
from dataclasses import dataclass

import pandas as pd
import streamlit as st

from app.dashboard.views.issue_data import (
    RECENT_DAYS,
    IssueFacets,
    _overview_quality_signal_masks,
    priority_color_names,
    priority_labels,
    recent_mask,
)
from app.dashboard.views.issue_panel import is_active_summary, select_summary

_HINTS = (
    ("MISSING_MILESTONE", "No milestone", "event_busy"),
    ("UNASSIGNED_OWNER", "Unassigned", "person_off"),
    ("MIXED_CLASSIFICATION", "Mixed", "label_off"),
)


@dataclass(frozen=True)
class SummaryItem:
    """One pill: what it counts and the board facets it applies when picked."""

    item_id: str
    label: str
    value: int
    icon: str
    color: str
    facets: IssueFacets

    def pill_label(self) -> str:
        """Return the pill text (Streamlit Markdown: icon or coloured dot)."""
        marker = f":{self.color}[●]" if self.color else f":material/{self.icon}:"
        return f"{marker} {self.label} **{self.value:,}**"


def build_summary(
    df: pd.DataFrame, now: pd.Timestamp | None = None
) -> list[tuple[str, list[SummaryItem]]]:
    """Compute the summary pills, grouped under a heading.

    Args:
        df: Overview issues, one row per issue.
        now: Reference time for the last-seven-days counts (default: now).

    Returns:
        ``(group heading, items)`` pairs in display order.
    """
    opened = df[df["state"] == "opened"]
    flow = [
        SummaryItem("open", "Open", len(opened), "radio_button_unchecked", "", {"state": "opened"}),
        SummaryItem(
            "new_recent", f"New {RECENT_DAYS}d", int(recent_mask(df, "created", now).sum()),
            "add_circle", "", {"state": "all", "recent": "created"},
        ),
        SummaryItem(
            "closed_recent", f"Closed {RECENT_DAYS}d", int(recent_mask(df, "closed", now).sum()),
            "check_circle", "", {"state": "closed", "recent": "closed"},
        ),
    ]

    labels = priority_labels(opened)
    ranks = (
        pd.to_numeric(opened["priority_rank"], errors="coerce")
        if "priority_rank" in opened.columns
        else pd.Series(float("nan"), index=opened.index)
    )
    stats = (
        pd.DataFrame({"label": labels, "rank": ranks})
        .groupby("label")
        .agg(count=("label", "size"), rank=("rank", "min"))
        .reset_index()
    )
    stats["unset"] = stats["label"] == "Unset"
    stats = stats.sort_values(["unset", "rank", "label"], na_position="last")
    colors = priority_color_names(df)
    priorities = [
        SummaryItem(
            f"priority_{row['label']}", str(row["label"]), int(row["count"]), "",
            colors.get(str(row["label"]), "gray"),
            {"state": "opened", "priority": str(row["label"])},
        )
        for row in stats.to_dict("records")
    ]

    masks = _overview_quality_signal_masks(df)
    hints = [
        SummaryItem(
            f"hint_{code.lower()}", label, int(masks[code].sum()), icon, "", {"signal": code}
        )
        for code, label, icon in _HINTS
    ]
    return [("Flow", flow), ("Open by priority", priorities), ("Hints", hints)]


def _label_for(items: dict[str, SummaryItem]) -> Callable[[str], str]:
    """Return the pill-label function for one group's items."""
    return lambda item_id: items[item_id].pill_label()


def _on_pick(pills_key: str, items: dict[str, SummaryItem]) -> None:
    picked = st.session_state.get(pills_key)
    item = items.get(picked) if picked else None
    select_summary(item.item_id if item else None, item.facets if item else {})


def render_summary_bar(groups: list[tuple[str, list[SummaryItem]]]) -> None:
    """Render the summary pills, one group after another, divided by a rule.

    Meant for a horizontal container (the board's toolbar row). Each group is
    a single-select ``st.pills``; the group name is its accessible label.

    Args:
        groups: The pills from ``build_summary``, computed once per full run.
    """
    for position, (heading, items) in enumerate(groups):
        if position:
            st.markdown('<span class="ov-divider"></span>', unsafe_allow_html=True, width="content")
        pills_key = "summary_" + heading.lower().replace(" ", "_")
        by_id = {item.item_id: item for item in items}
        active = next(
            (item.item_id for item in items if is_active_summary(item.item_id, item.facets)),
            None,
        )
        # Reflect the board's filter, so a pill is shown as picked only while
        # its filter is active.
        st.session_state[pills_key] = active
        st.pills(
            heading,
            list(by_id),
            format_func=_label_for(by_id),
            key=pills_key,
            selection_mode="single",
            label_visibility="collapsed",
            on_change=_on_pick,
            args=(pills_key, by_id),
            width="content",
        )
