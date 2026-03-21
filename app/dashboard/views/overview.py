"""Overview Page (Value Stream) for Layer 3 Dashboard.

Visualizes flow efficiency, bottlenecks, and aging.
Refactored to use Widget Registry where applicable.
"""

import os
from typing import Any, TypedDict, cast
from urllib.parse import parse_qs, urlparse

import gitlab
import pandas as pd
import streamlit as st
from gitlab.exceptions import GitlabError

from app.dashboard.theme import get_palette, get_plotly_font_color, with_alpha
from app.dashboard.utils import normalize_assignee_labels, sort_hierarchy
from app.dashboard.widgets import charts, tables


class _IssueNoteData(TypedDict):
    """Serialized GitLab issue note for Streamlit caching and rendering."""

    author_name: str
    author_username: str
    body: str
    created_at: str
    system: bool


class _IssueDetailsData(TypedDict):
    """Serialized GitLab issue details for the native modal view."""

    description: str
    notes: list[_IssueNoteData]
    title: str
    web_url: str


def _priority_color_key(value: object) -> str | None:
    """Normalize a displayed priority/severity value into a palette key."""
    if value is None or pd.isna(value):
        return "unset"

    normalized = str(value).strip().lower()
    if normalized in {"", "nan", "none", "<na>", "unset"}:
        return "unset"

    aliases = {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "p1": "p1",
        "p2": "p2",
        "p3": "p3",
        "1": "p1",
        "2": "p2",
        "3": "p3",
        "priority::1": "p1",
        "priority::2": "p2",
        "priority::3": "p3",
    }
    return aliases.get(normalized)


def _text_color_for_background(color: str) -> str:
    """Choose a readable text color for a hex background."""
    normalized = color.strip().lstrip("#")
    if len(normalized) == 3:
        normalized = "".join(ch * 2 for ch in normalized)
    if len(normalized) != 6:
        return "#ffffff"

    red = int(normalized[0:2], 16)
    green = int(normalized[2:4], 16)
    blue = int(normalized[4:6], 16)
    luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255.0
    return "#0d1120" if luminance > 0.62 else "#ffffff"


def _priority_cell_style(value: object) -> str | None:
    """Return CSS for the filtered-issues priority cell background."""
    color_key = _priority_color_key(value)
    if color_key is None:
        return None

    palette = get_palette()
    background = palette.get(color_key)
    if not background:
        return None

    return (
        f"background-color: {background}; "
        f"color: {_text_color_for_background(background)}; "
        "font-weight: 700;"
    )


def _selection_mask_for_value(df: pd.DataFrame, value: str) -> pd.Series:
    """Build a chart-selection mask against the overview DataFrame."""
    normalized_value = value.strip()
    severity_mask = df["severity"].astype(str).str.contains(
        normalized_value, case=False, na=False
    )
    if normalized_value.lower() == "low":
        severity_mask = severity_mask | df["severity"].isna() | df["severity"].astype(
            str
        ).str.strip().str.lower().isin(["none", "nan", "<na>", ""])

    assignee_mask = normalize_assignee_labels(df["assignee"]).str.contains(
        normalized_value, case=False, na=False
    )

    return (
        df["stage"].astype(str).str.contains(normalized_value, case=False, na=False)
        | assignee_mask
        | severity_mask
        | df["state"].astype(str).str.contains(normalized_value, case=False, na=False)
    )


def _is_local_issue_url(url: object) -> bool:
    """Return True when a URL points to a synthetic local dashboard issue."""
    if not isinstance(url, str) or not url:
        return False

    parsed_url = urlparse(url)
    query = parse_qs(parsed_url.query)
    return query.get("issue_source", [""])[0] == "local"


def _build_local_issue_details(row: pd.Series) -> _IssueDetailsData:
    """Build issue details directly from a local seeded row."""
    return {
        "title": str(row.get("title") or ""),
        "description": str(row.get("description") or "").strip(),
        "web_url": str(row.get("web_url") or ""),
        "notes": [],
    }


def _sync_local_issue_query_selection(df: pd.DataFrame) -> None:
    """Sync local issue query params into overview selection state."""
    if "web_url" not in df.columns or "project_id" not in df.columns or "iid" not in df.columns:
        return

    issue_source = str(st.query_params.get("issue_source", "")).strip()
    if issue_source != "local":
        return

    project_id_raw = str(st.query_params.get("issue_project_id", "")).strip()
    issue_iid_raw = str(st.query_params.get("issue_iid", "")).strip()

    try:
        project_id = int(project_id_raw)
        issue_iid = int(issue_iid_raw)
    except ValueError:
        return

    matches = df[(df["project_id"] == project_id) & (df["iid"] == issue_iid)]
    if matches.empty:
        return

    selected_row = matches.iloc[0]
    selected_url = str(selected_row.get("web_url") or "")
    if not selected_url:
        return

    if st.session_state.get("selected_issue_url") != selected_url:
        st.session_state["selected_issue_url"] = selected_url
        st.session_state["selected_issue_title"] = selected_row.get("title", "")
        st.session_state["show_issue_dialog"] = True


def _clear_local_issue_query_params() -> None:
    """Clear local issue deep-link query params after dismissing a modal."""
    for key in ("issue_source", "issue_project_id", "issue_iid"):
        if key in st.query_params:
            del st.query_params[key]


@st.cache_resource
def _get_gitlab_client() -> gitlab.Gitlab:
    """Create and cache the GitLab API client used by the overview dialog."""
    gitlab_url = os.environ.get("GITLAB_URL", "https://gitlab.com").strip() or "https://gitlab.com"
    private_token = os.environ.get("GITLAB_TOKEN", "").strip()

    if not private_token:
        raise ValueError("GITLAB_TOKEN environment variable is required to load issue details.")

    return gitlab.Gitlab(gitlab_url, private_token=private_token, timeout=15)


@st.cache_data(ttl=60)
def _load_issue_details(project_id: int, issue_iid: int) -> _IssueDetailsData:
    """Fetch the latest issue description and notes from the GitLab REST API."""
    client = _get_gitlab_client()
    project = client.projects.get(project_id)
    issue = project.issues.get(issue_iid)

    issue_attrs = issue.attributes
    notes: list[_IssueNoteData] = []

    for note in issue.notes.list(iterator=True, order_by="created_at", sort="asc"):
        note_attrs = note.attributes
        author = note_attrs.get("author") or {}
        notes.append(
            {
                "author_name": str(author.get("name") or ""),
                "author_username": str(author.get("username") or ""),
                "body": str(note_attrs.get("body") or ""),
                "created_at": str(note_attrs.get("created_at") or ""),
                "system": bool(note_attrs.get("system", False)),
            }
        )

    return {
        "title": str(issue_attrs.get("title") or ""),
        "description": str(issue_attrs.get("description") or ""),
        "web_url": str(issue_attrs.get("web_url") or ""),
        "notes": notes,
    }


def render_overview(
    df: pd.DataFrame,
    stage_descriptions: dict[str, str] | None = None,
    timeline_df: pd.DataFrame | None = None,
    highlight_milestone: str | None = None,
) -> None:
    """Render the Overview (Flow) page.

    Args:
        df: Filtered DataFrame with valid issues (milestone filter applied)
        stage_descriptions: Optional mapping of stage names to description strings
        timeline_df: Unfiltered DataFrame for the milestone timeline
        highlight_milestone: Active milestone name to highlight in the timeline
    """
    if df.empty:
        st.warning("No data available.")
        return

    _sync_local_issue_query_selection(df)

    unique_df = df.drop_duplicates(subset=["id"]) if "id" in df.columns else df
    _timeline_source = (timeline_df if timeline_df is not None else df).drop_duplicates(
        subset=["id"]
    ) if "id" in (timeline_df if timeline_df is not None else df).columns else (timeline_df or df)
    
    _active_ms = highlight_milestone if highlight_milestone and highlight_milestone != "All" else None

    chart_reset_suffix = st.session_state.get("chart_reset_counter", 0)
    palette = get_palette()
    panel_label_color = with_alpha(get_plotly_font_color(), 0.72)

    def handle_selection(
        selection_dict: dict[str, Any] | None,
        chart_id: str,
        stage_filter: str | None = None,
        state_filter: str | None = None,
    ) -> None:
        if selection_dict and selection_dict.get("selection", {}).get("points"):
            pts = selection_dict["selection"]["points"]
            prev_key = f"prev_sel_{chart_id}"
            
            if pts != st.session_state.get(prev_key):
                st.session_state[prev_key] = pts
                st.session_state["show_filtered_issues_dialog"] = True
                st.session_state["filtered_issues_selection"] = pts
                st.session_state["filtered_issues_stage"] = stage_filter
                st.session_state["filtered_issues_state"] = state_filter
                st.session_state["filtered_issues_source"] = chart_id
        else:
            prev_key = f"prev_sel_{chart_id}"
            st.session_state[prev_key] = []

    def render_panel_header(title: str, meta: str | None = None) -> None:
        """Render a compact, theme-aware panel heading."""
        meta_html = ""
        if meta:
            meta_html = (
                f"<span style='font-size:0.68rem; font-weight:700; "
                f"letter-spacing:0.14em; text-transform:uppercase; "
                f"color:{palette['primary']};'>{meta}</span>"
            )

        st.markdown(
            (
                "<div style='display:flex; align-items:center; justify-content:space-between; "
                "gap:0.75rem; margin-bottom:0.55rem;'>"
                f"<span style='font-size:0.78rem; font-weight:700; letter-spacing:0.12em; "
                f"text-transform:uppercase; color:{panel_label_color};'>{title}</span>"
                f"{meta_html}</div>"
            ),
            unsafe_allow_html=True,
        )

    # ROW 1
    st.markdown("##### OVERVIEW")
    r1c1, r1c2, r1c3 = st.columns([1, 1, 3])
    with r1c1, st.container(border=True):
        st.markdown("<div style='font-size:0.9rem; font-weight:bold; color:#555;'>OPEN ISSUES BY PRIORITY</div>", unsafe_allow_html=True)
        sel1 = charts.priority_donut(unique_df, config={"height": 200, "key": f"row1_priority_{chart_reset_suffix}", "show_legend": False})
        handle_selection(sel1, chart_id="open_donut", state_filter="opened")
    with r1c2, st.container(border=True):
        st.markdown("<div style='font-size:0.9rem; font-weight:bold; color:#555;'>CLOSED ISSUES BY PRIORITY</div>", unsafe_allow_html=True)
        sel2 = charts.priority_donut(
            unique_df, 
            config={
                "height": 200, 
                "key": f"row1_priority_closed_{chart_reset_suffix}", 
                "show_legend": False, 
                "state_filter": "closed", 
                "center_text": "CLOSED<br>ISSUES"
            }
        )
        handle_selection(sel2, chart_id="closed_donut", state_filter="closed")
    with r1c3, st.container(border=True):
        st.markdown("<div style='font-size:0.9rem; font-weight:bold; color:#555;'>DAILY NEW VS. CLOSED ISSUES</div>", unsafe_allow_html=True)
        sel3 = charts.daily_velocity_line(unique_df, config={"height": 200, "key": f"row1_velocity_{chart_reset_suffix}"})
        handle_selection(sel3, chart_id="velocity_chart")

    st.markdown("<br>", unsafe_allow_html=True)

    # ROW 2
    st.markdown("##### ISSUES BY WORKFLOW STATE")
    with st.container(border=True):
        if "stage_order" in unique_df.columns:
            stages = unique_df.groupby("stage")["stage_order"].min().sort_values().index.tolist()
        else:
            stages = unique_df["stage"].unique().tolist() if "stage" in unique_df.columns else []
            default_stage_order = ["Backlog", "To Do", "In Progress", "Review", "Testing", "Waiting for Release", "Done", "Closed"]
            stages = sorted(stages, key=lambda s: default_stage_order.index(s) if s in default_stage_order else len(default_stage_order))
        
        # Only show stages that actually have open issues otherwise it wastes horizontal space
        stages = [s for s in stages if not unique_df[(unique_df["stage"] == s) & (unique_df["state"] == "opened")].empty]
        
        if stages:
            stage_cols = st.columns(len(stages))
            for idx, stage_name in enumerate(stages):
                with stage_cols[idx]:
                    st.markdown(f"<div style='text-align:center; font-size:0.75rem; font-weight:bold; color:#777; margin-bottom:-10px;'>{stage_name.upper()}</div>", unsafe_allow_html=True)
                    stage_df = unique_df[unique_df["stage"] == stage_name]
                    sel = charts.priority_bar(
                        stage_df,
                        config={
                            "height": 200,
                            "key": f"row2_stage_bar_{idx}_{chart_reset_suffix}",
                        }
                    )
                    handle_selection(sel, chart_id=f"stage_bar_{idx}", stage_filter=stage_name)
        else:
            st.info("No stage data available.")

    st.markdown("<br>", unsafe_allow_html=True)

    # ROW 3
    st.markdown("##### DELIVERY SNAPSHOT")
    r3c1, r3c2, r3c3 = st.columns([2.2, 1.1, 1.4])
    with r3c1, st.container(border=True):
        render_panel_header("Release Timeline", meta="Milestones")
        key_suffix = st.session_state.get("timeline_reset_counter", 0)
        sel4 = charts.milestone_timeline(
            _timeline_source,
            config={
                "key": f"row3_timeline_{key_suffix}",
                "height": 150,
                "highlight_milestone": _active_ms,
            },
        )

        if sel4 and sel4.get("selection", {}).get("points"):
            pts = sel4["selection"]["points"]
            if pts and "customdata" in pts[0] and len(pts[0]["customdata"]) > 2:
                selected_ms = pts[0]["customdata"][2]

                if selected_ms == _active_ms:
                    st.session_state["overview_milestone_reset"] = True
                else:
                    st.session_state["overview_milestone_pending"] = selected_ms

                st.session_state.timeline_reset_counter = (
                    st.session_state.get("timeline_reset_counter", 0) + 1
                )
                st.rerun()
    with r3c2, st.container(border=True):
        render_panel_header("Open vs. Closed Issues")
        sel5 = charts.issue_state_bar(
            unique_df,
            config={
                "height": 150,
                "key": f"row3_issue_state_{chart_reset_suffix}",
            },
        )
        handle_selection(sel5, chart_id="issue_state_chart")
    with r3c3, st.container(border=True):
        render_panel_header("Issue Distribution by Assignee", meta="Top 5")
        sel6 = charts.assignee_distribution(
            unique_df,
            config={
                "height": 150,
                "key": f"row3_assignee_{chart_reset_suffix}",
                "limit": 5,
            },
        )
        handle_selection(sel6, chart_id="assignee_chart")

    st.markdown("<br>", unsafe_allow_html=True)

    # Display Filtered Issues Dialog
    if st.session_state.get("show_filtered_issues_dialog", False):
        pts = st.session_state.get("filtered_issues_selection", [])
        stage_filter = st.session_state.get("filtered_issues_stage")
        state_filter = st.session_state.get("filtered_issues_state")
        filtered_df = df.copy()
        
        source_chart = st.session_state.get("filtered_issues_source", "")
        
        if stage_filter:
            filtered_df = filtered_df[filtered_df["stage"] == stage_filter]
            
        if state_filter and state_filter != "all":
            filtered_df = filtered_df[filtered_df["state"] == state_filter]
            
        if pts:
            pt = pts[0]
            val = pt.get("label") or pt.get("x") or pt.get("y") or pt.get("text")
            
            if val and isinstance(val, str):
                if source_chart == "velocity_chart":
                    try:
                        selected_date = pd.to_datetime(val)
                        if selected_date.tzinfo is not None:
                            selected_date = selected_date.tz_localize(None)
                        selected_date = selected_date.floor("D")
                        
                        is_closed_trace = (pt.get("curveNumber") == 1)
                        if "customdata" in pt and pt["customdata"]:
                            is_closed_trace = (pt["customdata"][0] == "Closed")
                            
                        target_col = "closed_at" if is_closed_trace else "created_at"
                        target_state = "closed" if is_closed_trace else "opened"
                        
                        if target_col in filtered_df.columns:
                            col_dates = pd.to_datetime(filtered_df[target_col], errors="coerce")
                            if getattr(col_dates.dt, 'tz', None) is not None:
                                col_dates = col_dates.dt.tz_localize(None)
                            col_dates = col_dates.dt.floor("D")
                            filtered_df = filtered_df[(col_dates == selected_date) & (filtered_df["state"] == target_state)]
                    except Exception:
                        pass
                elif source_chart == "issue_state_chart":
                    selected_state = None
                    customdata = pt.get("customdata")
                    if isinstance(customdata, list) and customdata:
                        candidate_state = str(customdata[0]).strip().lower()
                        if candidate_state in {"opened", "closed"}:
                            selected_state = candidate_state

                    if selected_state is None:
                        normalized_val = val.strip().lower()
                        if "open" in normalized_val:
                            selected_state = "opened"
                        elif "closed" in normalized_val:
                            selected_state = "closed"

                    if selected_state is not None:
                        filtered_df = filtered_df[filtered_df["state"] == selected_state]
                    else:
                        filtered_df = pd.DataFrame(columns=filtered_df.columns)
                else:
                    # Simple loose string matching for any column
                    val = val.replace("<b>", "").replace("</b>", "").replace("<br>Open", "").replace("OPEN", "opened").replace("CLOSED", "closed").strip()

                    mask = _selection_mask_for_value(filtered_df, val)
                    if mask.any():
                        filtered_df = filtered_df[mask]
                    else:
                        filtered_df = pd.DataFrame(columns=filtered_df.columns)
                    
        if not filtered_df.empty:
            _show_filtered_issues_dialog(filtered_df)
        else:
            st.session_state["show_filtered_issues_dialog"] = False
            if source_chart:
                st.session_state[f"prev_sel_{source_chart}"] = []
            st.toast("No issues matched this selection.", icon="ℹ️")

    # Open single native issue dialog if selected from the table (not within filtered modal)
    elif st.session_state.get("show_issue_dialog", False):
        selected_url = st.session_state.get("selected_issue_url", "")
        if selected_url:
            selected_row = _get_selected_original_row(df)
            if selected_row is not None:
                _show_issue_dialog(selected_row)


@st.dialog("Filtered Issues", width="large")
def _show_filtered_issues_dialog(df: pd.DataFrame) -> None:
    """Render issue details grid in a dialog when a chart is clicked."""
    selected_url = st.session_state.get("selected_issue_url", "")
    if selected_url and st.session_state.get("show_issue_dialog", False):
        selected_row = _get_selected_original_row(df)
        if selected_row is not None:
            _render_issue_details_content(selected_row, is_nested=True)
            return

    if st.button("Close Modal", key="close_filtered_issues_modal", type="primary", use_container_width=True):
        st.session_state["show_filtered_issues_dialog"] = False
        st.session_state["chart_reset_counter"] = st.session_state.get("chart_reset_counter", 0) + 1
        st.session_state["filtered_issues_stage"] = None
        st.session_state["filtered_issues_state"] = None
        st.rerun()

    _render_issue_detail_grid(df, compact=False)

def _get_selected_original_row(
    df: pd.DataFrame,
) -> pd.Series | None:
    """Return the full original row for the currently selected issue, or None."""
    url = st.session_state.get("selected_issue_url", "")
    if not url or "web_url" not in df.columns:
        return None
    matches = df[df["web_url"] == url]
    if matches.empty:
        return None
    return cast(pd.Series, matches.iloc[0])


@st.dialog("Issue Details", width="large")
def _show_issue_dialog(row: pd.Series) -> None:
    """Render a native, read-only issue details dialog backed by the GitLab API."""
    _render_issue_details_content(row, is_nested=False)


def _render_issue_details_content(row: pd.Series, is_nested: bool = False) -> None:
    project_id_val = row.get("project_id")
    issue_iid_val = row.get("iid")

    if pd.isna(project_id_val) or pd.isna(issue_iid_val):
        st.error("This issue is missing the GitLab metadata required to load its details.")
        return

    project_id = int(project_id_val)
    issue_iid = int(issue_iid_val)
    is_local_issue = _is_local_issue_url(row.get("web_url"))

    if is_local_issue:
        issue_details = _build_local_issue_details(row)
    else:
        try:
            with st.spinner("Loading issue details from GitLab..."):
                issue_details = _load_issue_details(project_id, issue_iid)
        except ValueError as exc:
            st.error(str(exc))
            return
        except GitlabError as exc:
            st.error(f"Failed to load issue details from GitLab: {exc}")
            return

    web_url = _fmt(issue_details["web_url"] or row.get("web_url"))
    iid = _fmt(row.get("iid"))
    title = _fmt(issue_details["title"] or row.get("title"))

    header_col, action_col = st.columns([0.65, 0.35], gap="small")
    with header_col:
        st.markdown(f"### #{iid} — {_cell(title)}")
    with action_col:
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            if st.button("Back", use_container_width=True, type="primary", key="btn_top_back"):
                st.session_state["show_issue_dialog"] = False
                st.session_state["selected_issue_url"] = ""
                _clear_local_issue_query_params()
                if "selected_issue_title" in st.session_state:
                    st.session_state["selected_issue_title"] = ""
                st.rerun()
        with btn_col2:
            if web_url != "—":
                button_label = "Open locally" if is_local_issue else "Open in GitLab"
                st.link_button(button_label, web_url, type="primary", use_container_width=True)

    _render_tag_chips(row)
    st.divider()

    # ── BODY (70 / 30) ──────────────────────────────────────────────────────
    col_content, col_meta = st.columns([0.7, 0.3], gap="medium")

    with col_content:
        st.markdown("#### Description")
        description = issue_details["description"].strip()
        if description:
            st.markdown(description)
        else:
            st.caption("_No description provided._")
        if is_local_issue:
            st.caption("Local seeded issue details are rendered directly from parquet data.")

    with col_meta:
        _render_dialog_meta(row)

    # ── FOOTER ──────────────────────────────────────────────────────────────
    st.divider()
    st.markdown("#### Activity")
    if issue_details["notes"]:
        for note in issue_details["notes"]:
            author = note["author_name"] or note["author_username"] or "GitLab"
            avatar = "📌" if note["system"] else "💬"
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

    st.divider()

    if st.button("Back", use_container_width=True, type="primary", key="btn_bottom_back"):
        st.session_state["show_issue_dialog"] = False
        st.session_state["selected_issue_url"] = ""
        _clear_local_issue_query_params()
        if "selected_issue_title" in st.session_state:
            st.session_state["selected_issue_title"] = ""
        st.rerun()


def _chip_html(text: str, bg: str, fg: str) -> str:
    """Return an inline HTML badge/chip span."""
    return (
        f'<span style="background-color:{bg};color:{fg};border-radius:1em;'
        f'padding:3px 10px;font-size:0.78em;font-weight:500;'
        f'display:inline-block;white-space:nowrap;">{text}</span>'
    )


def _render_tag_chips(row: pd.Series) -> None:
    """Render priority, issue type, stage, and GitLab label chips inline."""
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

    raw_labels = row.get("labels")
    label_list: list[str] = []
    if isinstance(raw_labels, list):
        label_list = [
            str(lb).strip()
            for lb in raw_labels
            if str(lb).strip().lower() not in ("nan", "none", "")
        ]
    elif raw_labels is not None:
        raw = str(raw_labels).strip()
        if raw not in ("nan", "None", "[]", ""):
            label_list = [raw]

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
    days = row.get("days_in_stage")
    age = row.get("age_days")

    text_fields: list[tuple[str, str]] = [
        ("Stage", _fmt(row.get("stage"))),
        ("State", _fmt(row.get("state"))),
        ("Assignee", _fmt(row.get("assignee"))),
        ("Milestone", _fmt(row.get("milestone"))),
        ("Context", _fmt(row.get("context"))),
        ("Days in Stage", _fmt(row.get("days_in_stage")) if pd.notna(row.get("days_in_stage")) else "—"),
        ("Age", _fmt(row.get("age_days")) if pd.notna(row.get("age_days")) else "—"),
    ]
    for label, value in text_fields:
        if value != "—":
            st.markdown(f"**{label}**  \n{value}")


def _fmt(val: object) -> str:
    """Return a clean string value or '—' for missing/empty."""
    if val is None:
        return "—"
    s = str(val).strip()
    return "—" if s.lower() in ("nan", "none", "nat", "<na>", "") else s


def _format_timestamp(value: str, system_note: bool = False) -> str:
    """Format a GitLab timestamp for dialog metadata."""
    parsed = pd.to_datetime(value, utc=True, errors="coerce")
    if pd.isna(parsed):
        suffix = " · system note" if system_note else ""
        return f"{value}{suffix}" if value else "Unknown time"
    formatted = parsed.strftime("%Y-%m-%d %H:%M UTC")
    return f"{formatted} · system note" if system_note else formatted


def _cell(val: str) -> str:
    """Escape a string for safe use inside a markdown table cell."""
    return val.replace("|", "\\|").replace("\n", " ").replace("\r", "")


def _render_issue_detail_grid(df: pd.DataFrame, compact: bool = False) -> pd.DataFrame:
    """Render unified issue detail grid with drill-down filters.

    Args:
        df: DataFrame of issues to display
        compact: When True, show only title and assignee columns (used in
            side-by-side layout where the chart provides stage/priority context).

    Returns:
        The prepared display DataFrame (used by the caller for AI panel and
        detail card lookup).
    """

    popover_label = "⚙️ Filters"

    filter_controls_col, filter_popover_col = st.columns([0.72, 0.28], gap="small")

    with filter_controls_col:
        title_search = st.text_input(
            "Search Title",
            placeholder="Type to search issue titles...",
            key="filter_title",
            label_visibility="collapsed",
        )

    # --- Column Filters (Popover) ---
    with filter_popover_col, st.popover(popover_label, use_container_width=True):
        if "assignee" in df.columns:
            available_assignees = sorted(df["assignee"].dropna().unique().tolist())
            selected_assignees = st.multiselect(
                "Assignee",
                options=available_assignees,
                default=[],
                key="filter_assignee"
            )
        else:
            selected_assignees = []

    # --- Apply Filters ---
    display_df = df.copy()

    # Title search (case-insensitive)
    if title_search:
        display_df = display_df[display_df["title"].str.contains(title_search, case=False, na=False)]

    if selected_assignees:
        display_df = display_df[display_df["assignee"].isin(selected_assignees)]

    # Sort by Hierarchy (Parent -> Child) or Staleness
    if "parent_id" in display_df.columns:
        display_df = sort_hierarchy(display_df, parent_col="parent_id", id_col="iid", title_col="title")
    else:
        display_df = display_df.sort_values("days_in_stage", ascending=False)

    # Select Columns (keep 'id' for AI status lookup, 'iid' for numeric sorting)
    cols_to_show = [
        "id", "iid", "web_url", "title", "stage", "days_in_stage",
        "severity", "context", "milestone", "assignee",
    ]
    cols = [c for c in cols_to_show if c in display_df.columns]

    display_df = display_df[cols]

    # Reset index to ensure uniqueness for styling
    display_df = display_df.reset_index(drop=True)

    # Add AI Summary Status Column
    from pathlib import Path
    ai_storage_path = Path("data/ai")

    def check_summary_status(issue_id: object) -> str:
        if issue_id is None:
            return "✨"
        if isinstance(issue_id, int):
            issue_id_int = issue_id
        elif (
            isinstance(issue_id, str) and issue_id.isdigit()
        ) or (
            isinstance(issue_id, float) and issue_id.is_integer()
        ):
            issue_id_int = int(issue_id)
        else:
            return "✨"
        summary_file = ai_storage_path / f"chat_{issue_id_int}.parquet"
        return "📝" if summary_file.exists() else "✨"

    display_df.insert(0, "ai_status", display_df["id"].apply(check_summary_status))

    # Combine web_url + iid + title into a single clickable "title" column
    if "web_url" in display_df.columns and "title" in display_df.columns:
        iid_part = display_df["iid"].astype(str) if "iid" in display_df.columns else "?"
        display_df["title"] = (
            display_df["web_url"]
            + "#"
            + iid_part
            + " - "
            + display_df["title"].fillna("")
        )
        if "iid" in display_df.columns:
            display_df = display_df.drop(columns=["iid"])

    column_config = {
        "ai_status": st.column_config.TextColumn(
            "AI",
            width=40,
            help="📝 = Has AI summary | ✨ = No summary yet"
        ),
        "title": st.column_config.LinkColumn(
            "Title",
            display_text=r"#(.+)$",
            width="large",
            help="Click to open the issue URL",
        ),
        "assignee": st.column_config.TextColumn("Assignee", width="medium"),
        "stage": st.column_config.TextColumn("Stage", width="small"),
        "days_in_stage": st.column_config.NumberColumn(
            "Days in Stage",
            help="Days since last update in this stage",
            format="%d days",
        ),
        "severity": st.column_config.TextColumn("Priority", width="small"),
        "context": st.column_config.TextColumn("Context", width="small"),
        "milestone": st.column_config.TextColumn("Milestone", width="small"),
    }

    # Apply styling if context or priority columns are present.
    styler = None
    if "context" in display_df.columns or "severity" in display_df.columns:
        from app.dashboard.data_loader import load_labels

        label_styles = load_labels()

        def highlight_context(val: object) -> str | None:
            if not isinstance(val, str):
                return None
            style = label_styles.get(val)
            if style:
                bg_color = style.get("color", "#FFFFFF")
                text_color = style.get("text_color", "#000000")
                return f'background-color: {bg_color}; color: {text_color}'
            return None

        styler = display_df.style
        if "context" in display_df.columns:
            styler = styler.map(highlight_context, subset=["context"])
        if "severity" in display_df.columns:
            styler = styler.map(_priority_cell_style, subset=["severity"])

    # Compact mode: title + assignee only (stage/priority context via chart clicks)
    if compact:
        column_order = ["ai_status", "title", "assignee"]
    else:
        column_order = ["ai_status", "title", "stage", "days_in_stage", "severity", "milestone", "assignee"]
        if "context" in display_df.columns:
            column_order.insert(2, "context")

    # Persist selected issue for downstream panels (AI + detail card).
    # Call st.rerun() whenever the persisted URL changes so that the layout
    # decision in render_overview is always made with up-to-date state.
    selection_state = st.session_state.get("issue_drilldown_table", {})
    if hasattr(selection_state, "selection"):
        selection_state = selection_state.selection
    selected_indices = getattr(selection_state, "rows", [])
    if not selected_indices and isinstance(selection_state, dict):
        selected_indices = selection_state.get("rows", [])

    _prev_url = st.session_state.get("selected_issue_url", "")

    if selected_indices:
        selected_idx = selected_indices[0]
        if selected_idx < len(display_df):
            selected_row = display_df.iloc[selected_idx]
            _new_url = selected_row.get("web_url", "")
            if _new_url != _prev_url:
                st.session_state.selected_issue_url = _new_url
                st.session_state.selected_issue_title = selected_row.get("title", "")
                st.session_state["show_issue_dialog"] = True
                st.rerun()
    elif "issue_drilldown_table" in st.session_state and _prev_url != "":
        st.session_state.selected_issue_url = ""
        st.session_state.selected_issue_title = ""
        st.session_state["show_issue_dialog"] = False
        st.rerun()

    st.caption("Select an issue to view details and AI insights.")
    tables.issue_detail_grid(
        styler if styler is not None else display_df,
        config={
            "column_config": column_config,
            "column_order": column_order,
            "height": 640 if not compact else 400,
            "selection_mode": "single-row",
            "key": "issue_drilldown_table",
            "minimize_columns": False,
            "enable_filters": False,
        }
    )

    return display_df
