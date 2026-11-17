"""Issue board for the Overview page.

The Overview main panel is the workflow-state chart with the issue board below
it. Every chart click (the stage bars and the small charts in the right panel)
sets the board's filters, and Ctrl/Cmd+K opens a search panel with the same
filters. This module owns that filter state, the board and table, the issue
detail, the search panel, the URL state that makes the view shareable, and the
recently viewed list.
"""

import html
import json
from collections.abc import Callable
from typing import Any, cast

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from gitlab.exceptions import GitlabError

from app.dashboard.data_loader import load_labels
from app.dashboard.theme import get_plotly_font_color, get_priority_colors, with_alpha
from app.dashboard.utils import sort_hierarchy
from app.dashboard.views.issue_data import (
    FACET_QUERY_PREFIX,
    IssueFacets,
    _build_local_issue_details,
    _cell,
    _fmt,
    _format_timestamp,
    _is_local_issue_url,
    _issue_quality_hints,
    _issue_quality_hints_text,
    _load_issue_details,
    _normalize_issue_labels,
    _priority_cell_style,
    board_lanes,
    collapse_issue_contexts,
    facet_chips,
    facets_from_query,
    facets_from_selection,
    facets_to_query,
    filter_issues,
    lane_priority_counts,
    priority_color_names,
    without_facet,
)
from app.dashboard.views.issue_pages import render_page_bar
from app.dashboard.views.issue_search import inject_search_shortcut, render_search_box
from app.dashboard.widgets import tables
from app.dashboard.widgets.tables.issue_board import build_board_columns

_ISSUE_QUERY_KEYS = ("issue_source", "issue_project_id", "issue_iid")
_SUMMARY_QUERY_KEY = "summary"
_DEFAULT_FACETS: IssueFacets = {"state": "opened"}
_LANE_HEIGHT = 440
_TIME_PRESETS = {"30 Days": 30, "90 Days": 90, "1 Year": 365, "All Time": None}
_SIDEBAR_SELECTS = (
    ("team", "Domain / Team", "sidebar_team_selector"),
    ("context", "Context", "sidebar_context_selector"),
    ("milestone", "Milestone", "sidebar_milestone_selector"),
)
_VIEW_ICONS = {"Board": ":material/view_kanban:", "Table": ":material/table_rows:"}
# The issue list opens as a table; the board is one click away.
_DEFAULT_VIEW = "Table"


# --- Session state -----------------------------------------------------------

def _get_facets() -> IssueFacets:
    return cast(IssueFacets, st.session_state.get("issue_facets") or {})


def _with_default_state(facets: IssueFacets) -> IssueFacets:
    """Return the facets with open issues as the default state."""
    return cast(IssueFacets, {**_DEFAULT_FACETS, **facets})


def _reset_table() -> None:
    """Give the issue table a fresh key so stale row selections are dropped."""
    st.session_state["issue_table_version"] = (
        st.session_state.get("issue_table_version", 0) + 1
    )


def chart_key(base: str, chart_id: str) -> str:
    """Return the widget key of an Analytics chart.

    The key changes when the chart must drop its Plotly selection (its
    highlighted segment), that is, when the board's filter no longer comes
    from that chart.
    """
    resets: dict[str, int] = st.session_state.get("issue_chart_resets", {})
    return f"{base}_{resets.get(chart_id, 0)}"


def _reset_charts(except_chart: str | None = None) -> None:
    """Make the charts that hold a selection drop it, except ``except_chart``.

    Called whenever the filter changes another way than by a click in that
    chart, so the chart's highlight never outlives its filter.
    """
    if except_chart is None:
        st.session_state["issue_chart"] = None
    resets: dict[str, int] = st.session_state.setdefault("issue_chart_resets", {})
    signatures: dict[str, str] = st.session_state.setdefault("issue_chart_signatures", {})
    confirmed: dict[str, bool] = st.session_state.setdefault("issue_chart_confirmed", {})
    for chart_id in list(signatures):
        if chart_id != except_chart:
            resets[chart_id] = resets.get(chart_id, 0) + 1
            del signatures[chart_id]
            confirmed.pop(chart_id, None)


def apply_chart_selection(
    selection: dict[str, Any] | None,
    chart_id: str,
    stage_filter: str | None = None,
    state_filter: str | None = None,
) -> None:
    """Filter the board by a new selection in an Analytics chart.

    Plotly keeps reporting a selection on every rerun, so a selection is only
    applied when it differs from the last one seen for that chart. The chart's
    facets replace the board's filter (the search text is kept); the other
    charts drop their highlight. Clicking the segment that set the filter again
    removes it.
    """
    points = (selection or {}).get("selection", {}).get("points") or []
    signatures: dict[str, str] = st.session_state.setdefault("issue_chart_signatures", {})
    # Charts whose selection was reported again on a later run: Plotly keeps
    # it, so an empty selection from them afterwards is the user deselecting.
    # (A chart that redraws its highlight, like the donuts, loses the
    # selection on the next run instead and is never confirmed.)
    confirmed: dict[str, bool] = st.session_state.setdefault("issue_chart_confirmed", {})
    if not points:
        signatures.pop(chart_id, None)
        if confirmed.pop(chart_id, False) and st.session_state.get("issue_chart") == chart_id:
            _clear_chart_filter()
        return
    signature = json.dumps(points, sort_keys=True, default=str)
    if signatures.get(chart_id) == signature:
        confirmed[chart_id] = True
        return
    signatures[chart_id] = signature
    confirmed[chart_id] = False

    facets = facets_from_selection(chart_id, points, stage_filter, state_filter)
    current = _get_facets()
    query = current.get("query")
    # For a chart that redraws its highlight, a second click on the segment
    # arrives as a new selection of the same thing.
    if st.session_state.get("issue_chart") == chart_id and without_facet(
        current, "query"
    ) == facets:
        _clear_chart_filter()
    if query:
        facets["query"] = query
    st.session_state["issue_summary"] = None
    st.session_state["issue_chart"] = chart_id
    st.session_state["issue_facets"] = facets
    st.session_state["selected_issue_url"] = ""
    _reset_charts(except_chart=chart_id)
    _reset_table()
    st.rerun()


def _clear_chart_filter() -> None:
    """Drop the filter a chart set (a second click on its segment), keeping the
    search text. Analytics shows no filter chips, so this is how a chart filter
    is removed there.
    """
    query = _get_facets().get("query")
    _set_facets(IssueFacets(query=query) if query else IssueFacets())
    st.rerun()


def active_chart() -> str | None:
    """Return the chart whose click set the board's current filter, if any."""
    chart = st.session_state.get("issue_chart")
    return str(chart) if chart else None


def chart_priority_highlight(chart_id: str) -> str | None:
    """Return the priority a chart should draw highlighted, if any.

    Only for a chart whose own click set the board's current filter (charts
    whose click targets are invisible draw their highlight themselves).
    """
    if st.session_state.get("issue_chart") != chart_id:
        return None
    return _get_facets().get("priority")


def _sync_search_box(facets: IssueFacets) -> None:
    """Make the search field show a search changed elsewhere (a chip, the URL).

    The field keeps what was typed into it, so it gets a new key instead.
    """
    if facets.get("query") != _get_facets().get("query"):
        st.session_state["issue_search_version"] = (
            st.session_state.get("issue_search_version", 0) + 1
        )


def _set_search_query(query: str) -> None:
    """Apply the search field's text (typed, so the field already shows it)."""
    facets = dict(_get_facets())
    if query:
        facets["query"] = query
    else:
        facets.pop("query", None)
    st.session_state["issue_facets"] = cast(IssueFacets, facets)
    st.session_state["selected_issue_url"] = ""


def _set_facets(facets: IssueFacets) -> None:
    """Replace the board's facets (chip removal, clear all)."""
    _sync_search_box(facets)
    st.session_state["issue_facets"] = facets
    if not facets:
        st.session_state["issue_summary"] = None
    st.session_state["selected_issue_url"] = ""
    _reset_charts()
    _reset_table()


def _select_issue(url: str) -> None:
    """Open the issue with this URL in the detail pane, or close the pane.

    The table is reset each time so it comes back without a checked row.
    """
    st.session_state["selected_issue_url"] = url
    _reset_table()


def _selected_row(df: pd.DataFrame) -> pd.Series | None:
    url = str(st.session_state.get("selected_issue_url") or "")
    if not url or "web_url" not in df.columns:
        return None
    matches = df[df["web_url"] == url]
    return None if matches.empty else matches.iloc[0]


def is_active_summary(item_id: str, item_facets: IssueFacets) -> bool:
    """Return whether a summary pill was picked last and its filter still holds."""
    if st.session_state.get("issue_summary") != item_id:
        return False
    current = _with_default_state(_get_facets())
    return all(current.get(key) == value for key, value in item_facets.items())


def select_summary(item_id: str | None, item_facets: IssueFacets) -> None:
    """Set the board's base filter from a summary pill; ``None`` resets it.

    The pill's facets replace the previous ones; the search text is kept.
    Safe to call from a widget callback.
    """
    query = _get_facets().get("query")
    facets = cast(IssueFacets, dict(item_facets) if item_id else {})
    if query:
        facets["query"] = query
    st.session_state["issue_summary"] = item_id
    st.session_state["issue_facets"] = facets
    st.session_state["selected_issue_url"] = ""
    _reset_charts()
    _reset_table()


def _select_lane_priority(pills_key: str, stage: str) -> None:
    """Refine the board by a lane-header priority pill (widget callback).

    The lane pill adds ``stage`` and ``priority`` to the current filter; clearing
    it removes both again.
    """
    priority = st.session_state.get(pills_key)
    facets = without_facet(without_facet(_get_facets(), "stage"), "priority")
    if priority:
        facets = cast(
            IssueFacets, {**_with_default_state(facets), "stage": stage, "priority": priority}
        )
    st.session_state["issue_facets"] = facets
    st.session_state["selected_issue_url"] = ""
    _reset_charts()
    _reset_table()


# --- URL state ---------------------------------------------------------------

def _query_snapshot() -> dict[str, str]:
    return {
        key: str(st.query_params[key])
        for key in st.query_params
        if key.startswith(FACET_QUERY_PREFIX)
        or key in _ISSUE_QUERY_KEYS
        or key == _SUMMARY_QUERY_KEY
    }


def _issue_url_from_query(df: pd.DataFrame, params: dict[str, str]) -> str:
    required = {"web_url", "project_id", "iid"}
    if not required.issubset(df.columns):
        return ""
    try:
        project_id = int(params.get("issue_project_id", ""))
        issue_iid = int(params.get("issue_iid", ""))
    except ValueError:
        return ""
    matches = df[(df["project_id"] == project_id) & (df["iid"] == issue_iid)]
    return "" if matches.empty else str(matches.iloc[0].get("web_url") or "")


def sync_issue_state_from_query(df: pd.DataFrame) -> None:
    """Adopt the facets, picked summary pill and selected issue from the URL.

    The URL only differs from what this session last wrote on a fresh page
    load or when a shared or seeded link is opened, so in-app changes are never
    overwritten.
    """
    current = _query_snapshot()
    if current == st.session_state.get("issue_query_snapshot"):
        return
    st.session_state["issue_query_snapshot"] = current

    st.session_state["issue_summary"] = current.get(_SUMMARY_QUERY_KEY) or None
    from_url = facets_from_query(current)
    _sync_search_box(from_url)
    st.session_state["issue_facets"] = from_url
    st.session_state["selected_issue_url"] = _issue_url_from_query(df, current)


def _write_query_state(selected_row: pd.Series | None) -> None:
    """Mirror the facets, picked summary pill and selected issue into the URL."""
    desired: dict[str, str] = facets_to_query(_get_facets())
    summary_id = st.session_state.get("issue_summary")
    if summary_id:
        desired[_SUMMARY_QUERY_KEY] = str(summary_id)
    if selected_row is not None:
        desired["issue_project_id"] = str(int(selected_row["project_id"]))
        desired["issue_iid"] = str(int(selected_row["iid"]))
        if _is_local_issue_url(selected_row.get("web_url")):
            desired["issue_source"] = "local"

    current = _query_snapshot()
    if current != desired:
        for key in current:
            if key not in desired:
                del st.query_params[key]
        for key, value in desired.items():
            if current.get(key) != value:
                st.query_params[key] = value
    st.session_state["issue_query_snapshot"] = desired


# --- Sidebar filters ---------------------------------------------------------

def _sidebar_filter_chips() -> list[tuple[str, str, str]]:
    """Return ``(name, label, sidebar key)`` for each active sidebar filter.

    The sidebar is collapsed by default, so its filters are shown as chips on
    the board too. The time range uses the key ``active_range``.
    """
    chips = [
        (name, f"{label}: {st.session_state[sidebar_key]}", sidebar_key)
        for name, label, sidebar_key in _SIDEBAR_SELECTS
        if st.session_state.get(sidebar_key, "All") != "All"
    ]
    if st.session_state.get("active_range", "All Time") != "All Time":
        chips.append(("time", f"Time: {st.session_state['active_range']}", "active_range"))
    return chips


def _reset_sidebar_filter(sidebar_key: str) -> None:
    if sidebar_key == "active_range":
        _set_time_range("All Time")
    else:
        st.session_state[sidebar_key] = "All"


def _clear_all_filters() -> None:
    for _, _, sidebar_key in _sidebar_filter_chips():
        _reset_sidebar_filter(sidebar_key)
    _set_facets({})


def _set_time_range(label: str) -> None:
    """Apply a sidebar time-range preset, as its buttons do."""
    bounds = st.session_state.get("sidebar_date_bounds")
    if label not in _TIME_PRESETS or not bounds:
        return
    min_date, max_date = bounds
    days = _TIME_PRESETS[label]
    start = min_date if days is None else max(min_date, max_date - pd.Timedelta(days=days))
    st.session_state["date_range"] = (start, max_date)
    st.session_state["active_range"] = label


def finish_issue_state(df: pd.DataFrame) -> None:
    """Write the URL state and install the search shortcut.

    Call once per run, after the Overview is rendered.
    """
    _write_query_state(_selected_row(df))
    inject_search_shortcut()


# --- Issue list --------------------------------------------------------------

def _prepare_issue_rows(issues: pd.DataFrame) -> pd.DataFrame:
    """Sort the issues and shape them into the rows shown in the table."""
    rows = issues.sort_values(
        ["priority_rank", "days_in_stage"], ascending=[True, False], na_position="last"
    )
    if "parent_id" in rows.columns:
        rows = sort_hierarchy(rows, parent_col="parent_id", id_col="iid", title_col="title")

    columns = [
        "id", "iid", "web_url", "title", "stage", "days_in_stage",
        "priority", "context", "milestone", "assignee", "state", "labels",
    ]
    rows = rows[[column for column in columns if column in rows.columns]].copy()
    rows["priority"] = rows["priority"].astype(object).fillna("Unset")
    for column in ("stage", "milestone", "assignee"):
        if column in rows.columns:
            rows[column] = rows[column].astype(object).fillna("")
    rows["quality_hints"] = rows.apply(_issue_quality_hints_text, axis=1)
    rows = rows.reset_index(drop=True)
    rows["title"] = (
        rows["web_url"].astype(str)
        + "#"
        + rows["iid"].astype(str)
        + " - "
        + rows["title"].fillna("")
    )
    return rows


def _selected_table_rows(table_key: str) -> tuple[int, ...]:
    state = st.session_state.get(table_key, {})
    selection = getattr(state, "selection", None)
    if selection is None and isinstance(state, dict):
        selection = state.get("selection", {})
    rows = getattr(selection, "rows", None)
    if rows is None and isinstance(selection, dict):
        rows = selection.get("rows", [])
    return tuple(rows or ())


def _render_issue_table(rows: pd.DataFrame, facets: IssueFacets) -> None:
    """Render the issue table; selecting a row opens that issue."""
    page = render_page_bar("table", len(rows), on_change=_reset_table)
    rows = rows.iloc[page.start:page.stop]
    table_key = f"issue_table_{st.session_state.get('issue_table_version', 0)}"
    selected_rows = _selected_table_rows(table_key)
    if selected_rows and selected_rows[0] < len(rows):
        _select_issue(str(rows.iloc[selected_rows[0]]["web_url"]))
        st.rerun()

    label_styles = load_labels()
    context_options = sorted(
        {label for labels in rows["context"] for label in labels}
    ) if "context" in rows.columns else []
    column_config = {
        "title": st.column_config.LinkColumn(
            "Title",
            display_text=r"#(.+)$",
            width="large",
            help="Click to open the issue URL",
        ),
        "context": st.column_config.MultiselectColumn(
            "Context",
            options=context_options,
            color=[
                label_styles.get(option, {}).get("color", "gray")
                for option in context_options
            ] or None,
            width="medium",
        ),
        "stage": st.column_config.TextColumn("Stage", width="medium"),
        "days_in_stage": st.column_config.NumberColumn(
            "In stage",
            help="Days since the issue entered its current stage",
            format="%d d",
            width="small",
        ),
        "priority": st.column_config.TextColumn("Priority", width="small"),
        "milestone": st.column_config.TextColumn("Milestone", width="small"),
        "assignee": st.column_config.TextColumn("Assignee", width="medium"),
        "quality_hints": st.column_config.TextColumn("Quality hints", width="medium"),
    }

    column_order = ["title", "priority", "days_in_stage", "milestone", "assignee"]
    if "stage" not in facets:
        column_order.insert(1, "stage")
    if context_options:
        column_order.insert(1, "context")
    if rows["quality_hints"].ne("").any():
        column_order.append("quality_hints")

    grid_config = {
        "column_config": column_config,
        "column_order": column_order,
        # As tall as the page of rows: no scrolling inside.
        "height": "content",
        "selection_mode": "single-row",
        "key": table_key,
        "minimize_columns": False,
        "enable_filters": False,
    }
    tables.issue_detail_grid(
        rows.style.map(_priority_cell_style, subset=["priority"]), config=grid_config
    )


# --- Issue detail ------------------------------------------------------------

def _render_issue_detail(row: pd.Series, ordered_urls: list[str], back_label: str) -> None:
    """Render the selected issue next to the list."""
    project_id_val = row.get("project_id")
    issue_iid_val = row.get("iid")
    if pd.isna(project_id_val) or pd.isna(issue_iid_val):
        st.error("This issue is missing the GitLab metadata required to load its details.")
        return

    is_local_issue = _is_local_issue_url(row.get("web_url"))
    if is_local_issue:
        issue_details = _build_local_issue_details(row)
    else:
        try:
            with st.spinner("Loading issue details from GitLab..."):
                issue_details = _load_issue_details(int(project_id_val), int(issue_iid_val))
        except ValueError as exc:
            st.error(str(exc))
            return
        except GitlabError as exc:
            st.error(f"Failed to load issue details from GitLab: {exc}")
            return

    url = str(row.get("web_url") or "")
    web_url = _fmt(issue_details["web_url"] or row.get("web_url"))
    iid = _fmt(row.get("iid"))
    title = _fmt(issue_details["title"] or row.get("title"))

    position = ordered_urls.index(url) if url in ordered_urls else -1
    previous_url = ordered_urls[position - 1] if position > 0 else ""
    next_url = (
        ordered_urls[position + 1] if 0 <= position < len(ordered_urls) - 1 else ""
    )

    st.markdown(f"#### #{iid} — {_cell(title)}")
    with st.container(
        key="issue_detail_actions", horizontal=True, vertical_alignment="center"
    ):
        if st.button(
            "",
            icon=":material/chevron_left:",
            key="issue_detail_previous",
            help="Previous issue in the list",
            disabled=not previous_url,
        ):
            _select_issue(previous_url)
            st.rerun()
        if st.button(
            "",
            icon=":material/chevron_right:",
            key="issue_detail_next",
            help="Next issue in the list",
            disabled=not next_url,
        ):
            _select_issue(next_url)
            st.rerun()
        if web_url != "—":
            st.link_button(
                "Open locally" if is_local_issue else "Open in GitLab",
                web_url,
                type="primary",
            )
        if st.button(
            back_label,
            icon=":material/arrow_back:",
            key="issue_detail_close",
            type="tertiary",
        ):
            _select_issue("")
            st.rerun()

    _render_tag_chips(row, label_styles=load_labels())

    details_tab, activity_tab = st.tabs(["Details", "Activity"])
    with details_tab:
        col_content, col_meta = st.columns([0.68, 0.32], gap="medium")
        with col_content:
            description = issue_details["description"].strip()
            if description:
                st.markdown(description)
            else:
                st.caption("_No description provided._")
            if is_local_issue:
                st.caption("Local seeded issue details are rendered directly from parquet data.")
        with col_meta:
            _render_dialog_meta(row)

    with activity_tab:
        if issue_details["notes"]:
            for note in issue_details["notes"]:
                author = note["author_name"] or note["author_username"] or "GitLab"
                avatar = ":material/push_pin:" if note["system"] else ":material/chat:"
                with st.chat_message("assistant", avatar=avatar):
                    st.markdown(f"**{author}**")
                    st.caption(_format_timestamp(note["created_at"], system_note=note["system"]))
                    if note["body"].strip():
                        st.markdown(note["body"])
                    else:
                        st.caption("_Empty comment._")
        elif is_local_issue:
            st.caption("_Local seeded issues do not include GitLab activity history._")
        else:
            st.caption("_No comments yet._")


def _chip_html(text: str, bg: str, fg: str) -> str:
    """Return an inline HTML badge/chip span."""
    return (
        f'<span style="background-color:{bg};color:{fg};border-radius:1em;'
        f'padding:3px 10px;font-size:0.78em;font-weight:500;'
        f'display:inline-block;white-space:nowrap;">{text}</span>'
    )


def _render_tag_chips(
    row: pd.Series,
    label_styles: dict[str, dict[str, str]] | None = None,
) -> None:
    """Render priority, issue type, stage, and GitLab label chips inline.

    Args:
        row: Issue data row.
        label_styles: Pre-loaded label styles dict. When ``None`` the function
            loads styles itself (backward-compatible but slower).
    """
    if label_styles is None:
        from app.dashboard.data_loader import load_labels as _load_labels
        label_styles = _load_labels()

    chips_html: list[str] = []

    _severity_colors: dict[str, tuple[str, str]] = {
        "critical": ("#c0392b", "#ffffff"),
        "high":     ("#e67e22", "#ffffff"),
        "medium":   ("#f39c12", "#ffffff"),
        "low":      ("#27ae60", "#ffffff"),
    }

    for field, color_map in [
        ("severity", _severity_colors),
        ("issue_type", {}),
        ("stage", {}),
    ]:
        val = _fmt(row.get(field))
        if val == "—":
            continue
        bg, fg = color_map.get(val.lower(), ("#e0e0e0", "#333333"))
        chips_html.append(_chip_html(val, bg, fg))

    label_list = _normalize_issue_labels(row.get("labels"))
    for lb in label_list:
        style = label_styles.get(lb, {})
        bg = style.get("color", "#e0e0e0")
        fg = style.get("text_color", "#333333")
        chips_html.append(_chip_html(lb, bg, fg))

    if chips_html:
        st.markdown(
            '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:4px;">'
            + "".join(chips_html)
            + "</div>",
            unsafe_allow_html=True,
        )


def _render_dialog_meta(row: pd.Series) -> None:
    """Render metadata fields in the right column of the dialog body."""
    divider_color = with_alpha(get_plotly_font_color(), 0.14)
    label_color = with_alpha(get_plotly_font_color(), 0.72)
    value_color = get_plotly_font_color()

    text_fields: list[tuple[str, str]] = [
        ("Stage", _fmt(row.get("stage"))),
        ("State", _fmt(row.get("state"))),
        ("Assignee", _fmt(row.get("assignee"))),
        ("Milestone", _fmt(row.get("milestone"))),
        ("Context", _fmt(row.get("context"))),
        ("Days in Stage", _fmt(row.get("days_in_stage")) if pd.notna(row.get("days_in_stage")) else "—"),
        ("Age", _fmt(row.get("age_days")) if pd.notna(row.get("age_days")) else "—"),
    ]
    quality_hints = _issue_quality_hints(row)
    if quality_hints:
        text_fields.append(("Quality Hints", " • ".join(quality_hints)))
    for label, value in text_fields:
        if value != "—":
            st.markdown(
                _dialog_meta_item_html(
                    label=label,
                    value=value,
                    divider_color=divider_color,
                    label_color=label_color,
                    value_color=value_color,
                ),
                unsafe_allow_html=True,
            )


def _dialog_meta_item_html(
    label: str,
    value: str,
    divider_color: str,
    label_color: str,
    value_color: str,
) -> str:
    """Build HTML for a single dialog metadata section with a separator."""
    safe_label = html.escape(label)
    safe_value = html.escape(value)
    return (
        f'<div style="padding:0.1rem 0 0.7rem 0;'
        f'margin-bottom:0.7rem;border-bottom:1px solid {divider_color};">'
        f'<div style="font-size:0.72rem;letter-spacing:0.08em;'
        f'text-transform:uppercase;font-weight:700;color:{label_color};">'
        f"{safe_label}</div>"
        f'<div style="margin-top:0.28rem;font-size:0.98rem;line-height:1.35;'
        f'font-weight:600;color:{value_color};">{safe_value}</div>'
        "</div>"
    )


# --- Side list ----------------------------------------------------------------

def _scroll_side_list_to(selected_url: str) -> None:
    """Scroll the side list so the open issue's card is visible."""
    components.html(
        f"""
        <script>
        // issue {html.escape(selected_url)}
        window.setTimeout(() => {{
            const card = window.parent.document.querySelector(
                '[class*="issue_side_list-ibcard-"][class*="-ibsel"]'
            );
            let box = card && card.parentElement;
            while (box && !(box.scrollHeight > box.clientHeight + 4
                    && /auto|scroll/.test(getComputedStyle(box).overflowY))) {{
                box = box.parentElement;
            }}
            if (card && box) {{
                box.scrollTop += card.getBoundingClientRect().top
                    - box.getBoundingClientRect().top - 8;
            }}
        }}, 200);
        </script>
        """,
        height=0,
        width=0,
    )


# --- Lane headers ---------------------------------------------------------------

def _priority_bar_html(counts: list[tuple[str, int]]) -> str:
    """Thin stacked bar of a lane's issues by priority."""
    total = sum(count for _, count in counts)
    if not total:
        return '<div class="ib-pbar ib-pbar-empty"></div>'
    colors = get_priority_colors()
    segments = "".join(
        f'<span style="flex:{count};background:{colors.get(label, colors["Unset"])}" '
        f'title="{html.escape(label)}: {count}"></span>'
        for label, count in counts
    )
    return f'<div class="ib-pbar">{segments}</div>'


def _lane_header_renderer(
    facets: IssueFacets,
    lane_counts: dict[str, list[tuple[str, int]]],
    colors: dict[str, str],
) -> Callable[[int, str, pd.DataFrame], None]:
    """Build the board's lane header: title, priority bar, priority pills.

    Every lane header has the same three rows, so the lanes stay aligned.

    This header replaces the separate workflow-state chart: the bar shows the
    lane's mix of priorities, and a pill (a coloured dot and a count, the same
    dot colours as the summary's priority pills) refines the board to that
    stage and priority.
    """

    def render(index: int, stage: str, cards: pd.DataFrame) -> None:
        counts = lane_counts.get(stage, [])
        highlighted = facets.get("stage") == stage
        with st.container(key=f"lane_head_{index}", gap=None):
            st.markdown(
                f'<div class="ib-lane-head{" ib-lane-hl" if highlighted else ""}">'
                f"<b>{html.escape(stage)}</b> <small>{len(cards)}</small></div>"
                + _priority_bar_html(counts),
                unsafe_allow_html=True,
            )
            pills_key = f"lane_pills_{index}"
            by_label = dict(counts)
            active = facets.get("priority") if highlighted else None
            # Reflect the board's filter, so a pill is shown as picked only
            # while its filter is active.
            st.session_state[pills_key] = active if active in by_label else None
            st.pills(
                f"{stage} priority",
                list(by_label),
                format_func=lambda label: f":{colors.get(label, 'gray')}[●]{by_label[label]}",
                key=pills_key,
                selection_mode="single",
                label_visibility="collapsed",
                on_change=_select_lane_priority,
                args=(pills_key, stage),
                width="content",
            )

    return render


# --- Panel -------------------------------------------------------------------

def _render_panel_header(
    facets: IssueFacets,
    count_caption: str,
    toolbar: Callable[[], None] | None,
    show_filters: bool,
) -> str:
    """Render the board's header: one toolbar row, then chips if filtered.

    The toolbar row holds the caller's ``toolbar`` (the summary pills) on the
    left and the search button and the view switch on the right. The active
    filters and the issue count get a second row only while there are filters;
    without filters the count is on the "Open" summary pill.

    Returns:
        The active view, ``"Board"`` or ``"Table"``.
    """
    persisted_view = st.session_state.get("filtered_issues_view", _DEFAULT_VIEW)
    with st.container(
        key="issue_panel_toolbar",
        horizontal=True,
        horizontal_alignment="distribute",
        vertical_alignment="center",
    ):
        with st.container(
            key="issue_panel_toolbar_left",
            horizontal=True,
            vertical_alignment="center",
        ):
            if toolbar is not None:
                toolbar()
        with st.container(
            key="issue_panel_actions",
            horizontal=True,
            horizontal_alignment="right",
            vertical_alignment="center",
            width="content",
        ):
            query = str(facets.get("query", ""))
            typed = render_search_box(
                query, int(st.session_state.get("issue_search_version", 0))
            )
            if typed != query:
                _set_search_query(typed)
                st.rerun()
            view = st.segmented_control(
                "View",
                ["Board", "Table"],
                format_func=_VIEW_ICONS.__getitem__,
                key="filtered_issues_view_choice",
                default=persisted_view,
                label_visibility="collapsed",
                help="Board or table view",
            ) or persisted_view
    st.session_state["filtered_issues_view"] = view

    chips = facet_chips(facets)
    sidebar_chips = _sidebar_filter_chips()
    if show_filters and (chips or sidebar_chips):
        with st.container(
            key="issue_panel_chips", horizontal=True, vertical_alignment="center"
        ):
            for facet_key, label in chips:
                if st.button(
                    label,
                    icon=":material/close:",
                    key=f"issue_chip_{facet_key}",
                    help="Remove this filter",
                ):
                    _set_facets(without_facet(facets, facet_key))
                    st.rerun()
            for name, label, sidebar_key in sidebar_chips:
                st.button(
                    label,
                    icon=":material/close:",
                    key=f"issue_chip_sidebar_{name}",
                    help="Remove this filter",
                    on_click=_reset_sidebar_filter,
                    args=(sidebar_key,),
                )
            st.button(
                "Clear all",
                type="tertiary",
                key="issue_chip_clear",
                on_click=_clear_all_filters,
            )
            st.caption(count_caption)
    return str(view)


def render_issue_panel(
    df: pd.DataFrame,
    chart_stages: list[str],
    toolbar: Callable[[], None] | None = None,
    show_filters: bool = True,
    lane_headers: bool = True,
) -> None:
    """Render the issue board (or table) for the active facets.

    The board and the table apply the same facets. The board keeps a lane for
    every chart stage, empty ones included, and marks the stage facet's lane.

    Args:
        df: Overview issues after the sidebar filters, one row per issue and
            context.
        chart_stages: Stages with open issues, in workflow order (the lanes).
        toolbar: Renders the left part of the board's toolbar row.
        show_filters: Show the active filters as chips, with the issue count.
            Off where the charts above show the filters (Analytics).
        lane_headers: Show a header above each lane. Off where the stages are
            shown above the board (Analytics).
    """
    facets = _get_facets()
    effective = _with_default_state(facets)
    highlight_stage = facets.get("stage")

    issues = collapse_issue_contexts(filter_issues(df, effective))
    # Lane headers count what the board shows without the stage and priority
    # refinement, so every lane keeps its full priority mix, and the lanes stay
    # even when the refinement matches nothing.
    header_facets = without_facet(without_facet(effective, "stage"), "priority")
    header_issues = collapse_issue_contexts(filter_issues(df, header_facets))
    lanes = board_lanes(chart_stages, header_issues)
    lane_counts = lane_priority_counts(header_issues)

    selected_row = _selected_row(df)
    selected_url = "" if selected_row is None else str(selected_row["web_url"])

    noun = "issue" if len(issues) == 1 else "issues"
    count_caption = f"{len(issues)} {noun}"

    with st.container(border=True, key="issue_panel"):
        # Keyed so the toolbar and the chips stay pinned while the board scrolls.
        with st.container(key="issue_panel_head"):
            view = _render_panel_header(facets, count_caption, toolbar, show_filters)

        if selected_row is not None:
            list_caption = ""
            if view == "Board":
                # The side list is the lane the issue was opened from.
                columns = build_board_columns(issues, lanes)
                lane = next(
                    (
                        (stage, cards)
                        for stage, cards in columns
                        if selected_url in set(cards["web_url"].astype(str))
                    ),
                    None,
                )
                if lane is None:
                    ordered = pd.concat([cards for _, cards in columns]) if columns else issues
                else:
                    ordered = lane[1]
                    noun = "issue" if len(ordered) == 1 else "issues"
                    list_caption = f"{lane[0]} · {len(ordered)} {noun}"
            else:
                rows = _prepare_issue_rows(issues) if not issues.empty else None
                ordered = (
                    issues.set_index("id").loc[rows["id"]].reset_index()
                    if rows is not None
                    else issues
                )
            list_col, detail_col = st.columns([0.3, 0.7], gap="medium")
            with list_col:
                if list_caption:
                    st.caption(list_caption)
                clicked_url = tables.issue_card_list(
                    ordered,
                    {
                        "key": "issue_side_list",
                        "height": _LANE_HEIGHT + 60,
                        "selected_url": selected_url,
                    },
                )
                if clicked_url and clicked_url != selected_url:
                    _select_issue(clicked_url)
                    st.rerun()
                _scroll_side_list_to(selected_url)
            with detail_col:
                back_label = "Back to board" if view == "Board" else "Back to table"
                _render_issue_detail(
                    selected_row, ordered["web_url"].astype(str).tolist(), back_label
                )
        elif view == "Board":
            if issues.empty and not lane_counts:
                st.info("No issues match the current filters.")
            else:
                longest_lane = max(
                    (len(cards) for _, cards in build_board_columns(issues, lanes)),
                    default=0,
                )
                cards_page = render_page_bar("board", longest_lane, on_change=lambda: None)
                with st.container(key="issue_board_wrap"):
                    clicked_url = tables.issue_board(
                        issues,
                        {
                            "key": "issue_board",
                            "stages": lanes,
                            "highlight_stage": highlight_stage,
                            # As tall as the page of cards: no scrolling inside.
                            "lane_height": None,
                            "card_start": cards_page.start,
                            "max_cards": cards_page.stop - cards_page.start,
                            "min_columns": len(chart_stages),
                            "lane_headers": lane_headers,
                            "lane_header": _lane_header_renderer(
                                facets, lane_counts, priority_color_names(df)
                            ),
                        },
                    )
                if clicked_url:
                    _select_issue(clicked_url)
                    st.rerun()
        elif issues.empty:
            st.info("No issues match the current filters.")
        else:
            _render_issue_table(_prepare_issue_rows(issues), facets)
