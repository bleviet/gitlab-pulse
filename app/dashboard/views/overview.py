"""Overview Page (Value Stream) for Layer 3 Dashboard.

Visualizes flow efficiency, bottlenecks, and aging.
Refactored to use Widget Registry where applicable.
"""

import pandas as pd
import streamlit as st

from app.dashboard.utils import sort_hierarchy
from app.dashboard.widgets import charts, features, tables


def render_overview(
    df: pd.DataFrame,
    stage_descriptions: dict[str, str] | None = None
) -> None:
    """Render the Overview (Flow) page.

    Args:
        df: Filtered DataFrame with valid issues
        stage_descriptions: Optional mapping of stage names to description strings
    """
    if df.empty:
        st.warning("No data available.")
        return

    unique_df = df.drop_duplicates(subset=["id"]) if "id" in df.columns else df

    # Top Row: Milestone Timeline (collapsed by default, only shown when milestones exist)
    if "milestone_id" in df.columns and not df["milestone_id"].isnull().all():
        with st.expander("📅 Milestone Timeline", expanded=True):
            charts.milestone_timeline(unique_df, config={"key": "overview_timeline"})

    # Side-by-side layout: issue list on the left, chart on the right
    col_list, col_chart = st.columns([1, 1], gap="medium")

    with col_chart, st.expander("Visual Analysis", expanded=True):
        # Stage distribution rotated 90° CCW (vertical bars: stages on x-axis)
        stage_selection = charts.stage_distribution(
            unique_df,
            config={
                "stage_descriptions": stage_descriptions,
                "key": "flow_chart_stage_dist",
                "orientation": "v",
            }
        )

    # Apply interactive filters (apply to original DF to allow exploring contexts)
    filtered_df = df.copy()

    if stage_selection and stage_selection.get("selection", {}).get("points"):
        selected_points = stage_selection["selection"]["points"]
        masks = []
        for point in selected_points:
            # Vertical chart: x=stage (string), y=count (number)
            # Detect stage value robustly: it is the string dimension
            x_val = point.get("x")
            y_val = point.get("y")
            stage = x_val if isinstance(x_val, str) else y_val

            severity = point.get("customdata", [None])[0]

            mask = (filtered_df["stage"] == stage)
            if severity:
                if severity == "Unset":
                    mask &= (
                        filtered_df["severity"].isna() |
                        (filtered_df["severity"].astype(str).str.strip().str.lower().isin(["unset", "none", "nan", "<na>", ""]))
                    )
                else:
                    mask &= (filtered_df["severity"].astype(str).str.strip().str.lower() == severity.lower())

            masks.append(mask)

        if masks:
            final_mask = pd.Series(False, index=filtered_df.index)
            for m in masks:
                final_mask |= m
            filtered_df = filtered_df[final_mask]

    # Determine whether a selection is persisted before rendering the table
    # so we can decide whether to split the issue list column.
    has_persisted = st.session_state.get("selected_issue_url", "") != ""

    with col_list, st.expander("📋 Issue List", expanded=True):
        if has_persisted:
            tbl_col, det_col = st.columns([1.2, 0.8], gap="medium")
            with tbl_col:
                display_df = _render_issue_detail_grid(filtered_df, compact=True)
            with det_col:
                selected_row = _get_selected_original_row(df, display_df)
                if selected_row is not None:
                    _render_selected_issue_panel(selected_row)
        else:
            display_df = _render_issue_detail_grid(filtered_df, compact=True)
            selected_row = None

    has_selection = selected_row is not None if has_persisted else False

    # AI Summary in the right column (below Visual Analysis)
    with col_chart, st.expander("🤖 AI Summary", expanded=has_selection):
        if has_selection:
            features.ai_assistant(df, display_df)
        else:
            st.caption("Select an issue from the list to view AI insights.")


def _get_selected_original_row(
    df: pd.DataFrame,
    display_df: pd.DataFrame,
) -> pd.Series | None:
    """Return the full original row for the currently selected issue, or None."""
    url = st.session_state.get("selected_issue_url", "")
    if not url or "web_url" not in df.columns:
        return None
    matches = df[df["web_url"] == url]
    if matches.empty:
        return None
    return matches.iloc[0]


def _fmt(val: object) -> str:
    """Return a clean string value or '—' for missing/empty."""
    if val is None:
        return "—"
    s = str(val).strip()
    return "—" if s.lower() in ("nan", "none", "nat", "<na>", "") else s


def _cell(val: str) -> str:
    """Escape a string for safe use inside a markdown table cell."""
    return val.replace("|", "\\|").replace("\n", " ").replace("\r", "")


def _label_chips_html(label_list: list[str], label_styles: dict) -> str:
    """Build GitLab-style label chip HTML for each label on its own line."""
    chips = []
    for lb in label_list:
        style = label_styles.get(lb, {})
        bg = style.get("color", "#e0e0e0")
        fg = style.get("text_color", "#333333")
        chips.append(
            f'<span style="'
            f"background-color:{bg};"
            f"color:{fg};"
            f"border-radius:1em;"
            f"padding:2px 10px;"
            f"font-size:0.78em;"
            f"font-weight:500;"
            f"display:inline-block;"
            f'margin:2px 0;">{lb}</span>'
        )
    return "<br>".join(chips)


def _render_selected_issue_panel(row: pd.Series) -> None:
    """Render a compact textual detail view for the selected issue."""
    web_url = _fmt(row.get("web_url"))
    iid = _fmt(row.get("iid"))
    title = _fmt(row.get("title"))

    if web_url != "—":
        st.markdown(f"**[#{iid} — {_cell(title)}]({web_url})**")
    else:
        st.markdown(f"**#{iid} — {_cell(title)}**")

    st.divider()

    days = row.get("days_in_stage")
    days_str = f"{int(days)}d" if pd.notna(days) else "—"
    age = row.get("age_days")
    age_str = f"{int(age)}d" if pd.notna(age) else "—"
    cycle = row.get("cycle_time")
    cycle_str = f"{int(cycle)}d" if pd.notna(cycle) else "—"

    fields: list[tuple[str, str]] = [
        ("Team", _fmt(row.get("team"))),
        ("Milestone", _fmt(row.get("milestone"))),
        ("Priority", _fmt(row.get("severity"))),
        ("Type", _fmt(row.get("issue_type"))),
        ("State", _fmt(row.get("state"))),
        ("Assignee", _fmt(row.get("assignee"))),
        ("Stage", _fmt(row.get("stage"))),
        ("Days in Stage", days_str),
        ("Age", age_str),
        ("Cycle Time", cycle_str),
        ("Context", _fmt(row.get("context"))),
    ]

    rows = "\n".join(
        f"| **{label}** | {_cell(value)} |"
        for label, value in fields
        if value != "—"
    )
    st.markdown(f"| | |\n|---|---|\n{rows}")

    # Labels — rendered as GitLab-style chips (HTML), one per line
    raw_labels = row.get("labels")
    label_list: list[str] = []
    if hasattr(raw_labels, "__iter__") and not isinstance(raw_labels, str):
        label_list = [
            str(lb).strip()
            for lb in raw_labels
            if str(lb).strip().lower() not in ("nan", "none", "")
        ]
    elif raw_labels is not None:
        raw = str(raw_labels).strip()
        if raw not in ("nan", "None", "[]", ""):
            label_list = [raw]

    if label_list:
        from app.dashboard.data_loader import load_labels as _load_labels
        label_styles = _load_labels()
        st.markdown(
            _label_chips_html(label_list, label_styles),
            unsafe_allow_html=True,
        )

    # Description (collapsible)
    desc = _fmt(row.get("description"))
    if desc != "—":
        with st.expander("📄 Description", expanded=False):
            st.markdown(desc[:3000])


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

    # --- Column Filters (Expandable) ---
    with st.expander("🔍 Filters", expanded=False):
        # Row 1: Title search (full width)
        title_search = st.text_input(
            "Search Title",
            placeholder="Type to search issue titles...",
            key="filter_title"
        )

        # Row 2: Multiselect filters (3 columns)
        filter_cols_row1 = st.columns(3)

        # 1. Stage Filter
        with filter_cols_row1[0]:
            available_stages = sorted(
                df["stage"].unique(),
                key=lambda s: df[df["stage"] == s]["stage_order"].min()
            )
            selected_stages = st.multiselect(
                "Stage",
                options=available_stages,
                default=[],
                key="filter_stage"
            )

        # 2. Priority Filter
        with filter_cols_row1[1]:
            if "severity" in df.columns:
                available_priorities = sorted(df["severity"].dropna().unique().tolist())
                selected_priorities = st.multiselect(
                    "Priority",
                    options=available_priorities,
                    default=[],
                    key="filter_priority"
                )
            else:
                selected_priorities = []

        # 3. Context Filter
        with filter_cols_row1[2]:
            if "context" in df.columns:
                available_contexts = sorted(df["context"].dropna().unique().tolist())
                selected_contexts = st.multiselect(
                    "Context",
                    options=available_contexts,
                    default=[],
                    key="filter_context"
                )
            else:
                selected_contexts = []

        # Row 3: Milestone and Assignee (2 columns)
        filter_cols_row2 = st.columns(2)

        # 4. Milestone Filter
        with filter_cols_row2[0]:
            if "milestone" in df.columns:
                available_milestones = sorted(df["milestone"].dropna().unique().tolist())
                selected_milestones = st.multiselect(
                    "Milestone",
                    options=available_milestones,
                    default=[],
                    key="filter_milestone"
                )
            else:
                selected_milestones = []

        # 5. Assignee Filter
        with filter_cols_row2[1]:
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

    if selected_stages:
        display_df = display_df[display_df["stage"].isin(selected_stages)]

    if selected_priorities:
        display_df = display_df[display_df["severity"].isin(selected_priorities)]

    if selected_contexts:
        display_df = display_df[display_df["context"].isin(selected_contexts)]

    if selected_milestones:
        display_df = display_df[display_df["milestone"].isin(selected_milestones)]

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
        if pd.isna(issue_id):
            return "✨"
        summary_file = ai_storage_path / f"chat_{int(issue_id)}.parquet"
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
            help="Click to open in GitLab",
        ),
        "assignee": st.column_config.TextColumn("Assignee", width="small"),
        "stage": st.column_config.TextColumn("Stage", width="small"),
        "days_in_stage": st.column_config.NumberColumn(
            "Days in Stage",
            help="Days since last update in this stage",
            format="%d days",
        ),
        "severity": st.column_config.TextColumn("Priority", width="small"),
        "context": st.column_config.TextColumn("Context", width="small"),
        "milestone": st.column_config.TextColumn("Milestone", width="medium"),
    }

    # Apply styling if Context column exists
    styler = None
    if "context" in display_df.columns:
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

        styler = display_df.style.map(highlight_context, subset=["context"])

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
        _page = st.session_state.get("issue_drilldown_table_page", 0)
        _page_size = st.session_state.get("issue_drilldown_table_page_size", 25)
        _offset = 0 if isinstance(_page_size, str) else _page * int(_page_size)
        selected_idx = selected_indices[0] + _offset
        if selected_idx < len(display_df):
            selected_row = display_df.iloc[selected_idx]
            _new_url = selected_row.get("web_url", "")
            if _new_url != _prev_url:
                st.session_state.selected_issue_url = _new_url
                st.session_state.selected_issue_title = selected_row.get("title", "")
                st.rerun()
    elif "issue_drilldown_table" in st.session_state and _prev_url != "":
        st.session_state.selected_issue_url = ""
        st.session_state.selected_issue_title = ""
        st.rerun()

    st.caption("Select an issue to view details and AI insights.")
    tables.issue_detail_grid(
        styler if styler is not None else display_df,
        config={
            "column_config": column_config,
            "column_order": column_order,
            "selection_mode": "single-row",
            "key": "issue_drilldown_table",
            "minimize_columns": False,
            "enable_filters": False,
        }
    )

    return display_df
