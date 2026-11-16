"""Issue data helpers for the Overview page.

Pure helpers shared by the Overview charts and the issue panel: quality hints,
chart-selection masks, issue-list facets, search, and issue detail loading.
"""

import ast
import os
import re
from collections.abc import Mapping
from difflib import SequenceMatcher
from typing import TypedDict
from urllib.parse import parse_qs, urlparse

import gitlab
import pandas as pd
import streamlit as st

from app.dashboard.theme import get_palette, with_alpha
from app.dashboard.utils import normalize_assignee_labels


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


_ISSUE_GRID_SEARCH_COLUMNS = (
    "iid",
    "title",
    "stage",
    "days_in_stage",
    "priority",
    "context",
    "milestone",
    "assignee",
)
_OVERVIEW_SIGNAL_UNASSIGNED = "UNASSIGNED_OWNER"
_OVERVIEW_SIGNAL_MISSING_MILESTONE = "MISSING_MILESTONE"
_OVERVIEW_SIGNAL_MIXED_CLASSIFICATION = "MIXED_CLASSIFICATION"


def _has_multiple_classification_labels(labels: object) -> bool:
    """Return True when an issue carries multiple labels in one classification bucket."""
    normalized_labels = [label.lower() for label in _normalize_issue_labels(labels)]
    classification_prefixes = ("type::", "severity::", "priority::")
    return any(
        sum(label.startswith(prefix) for label in normalized_labels) > 1
        for prefix in classification_prefixes
    )


def _mixed_classification_hints(labels: object) -> list[str]:
    """Describe the conflicting classification labels carried by an issue."""
    label_groups = {
        "type::": "Mixed type labels",
        "severity::": "Mixed severity labels",
        "priority::": "Mixed priority labels",
    }
    normalized_labels = _normalize_issue_labels(labels)

    hints: list[str] = []
    for prefix, label_name in label_groups.items():
        matches = [label for label in normalized_labels if label.lower().startswith(prefix)]
        if len(matches) > 1:
            hints.append(f"{label_name}: {' + '.join(matches)}")
    return hints


def _is_missing_milestone(value: object) -> bool:
    """Return True when milestone information is absent."""
    if value is None:
        return True
    return str(value).strip().lower() in {"", "none", "nan", "<na>"}


def _issue_quality_hints(row: pd.Series) -> list[str]:
    """Build the user-facing quality hint messages for a single issue row."""
    if row.get("state") != "opened":
        return []

    hints = _mixed_classification_hints(row.get("labels"))

    assignee_label = normalize_assignee_labels(pd.Series([row.get("assignee")])).iloc[0]
    if assignee_label == "Unassigned":
        hints.append("Unassigned owner")

    if _is_missing_milestone(row.get("milestone")):
        hints.append("Missing milestone")

    return hints


def _issue_quality_hints_text(row: pd.Series) -> str:
    """Return quality hint messages as a compact string for table display."""
    return " | ".join(_issue_quality_hints(row))


def _build_overview_quality_signal_df(df: pd.DataFrame) -> pd.DataFrame:
    """Build the curated Overview quality-signal dataset from the current issues."""
    if df.empty:
        return pd.DataFrame(columns=["error_code"])

    signal_frames: list[pd.DataFrame] = []

    for signal_code, signal_mask in _overview_quality_signal_masks(df).items():
        if signal_mask.any():
            signal_df = df.loc[signal_mask].copy()
            signal_df["error_code"] = signal_code
            signal_frames.append(signal_df)

    if not signal_frames:
        return pd.DataFrame(columns=["error_code"])

    return pd.concat(signal_frames, ignore_index=True)


def _overview_quality_signal_masks(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Return boolean masks for the Overview quality-signal criteria."""
    if df.empty:
        empty_mask = pd.Series(dtype=bool)
        return {
            _OVERVIEW_SIGNAL_MIXED_CLASSIFICATION: empty_mask,
            _OVERVIEW_SIGNAL_UNASSIGNED: empty_mask,
            _OVERVIEW_SIGNAL_MISSING_MILESTONE: empty_mask,
        }

    is_opened_mask = (
        df["state"].eq("opened")
        if "state" in df.columns
        else pd.Series(True, index=df.index)
    )

    mixed_classification_mask = (
        df["labels"].apply(_has_multiple_classification_labels)
        if "labels" in df.columns
        else pd.Series(False, index=df.index)
    )
    assignee_series = (
        normalize_assignee_labels(df["assignee"])
        if "assignee" in df.columns
        else pd.Series("Assigned", index=df.index)
    )
    milestone_series = (
        df["milestone"]
        if "milestone" in df.columns
        else pd.Series(None, index=df.index, dtype="object")
    )
    missing_milestone_mask = milestone_series.apply(_is_missing_milestone)

    return {
        _OVERVIEW_SIGNAL_MIXED_CLASSIFICATION: mixed_classification_mask & is_opened_mask,
        _OVERVIEW_SIGNAL_UNASSIGNED: assignee_series.eq("Unassigned") & is_opened_mask,
        _OVERVIEW_SIGNAL_MISSING_MILESTONE: missing_milestone_mask & is_opened_mask,
    }


def _selection_mask_for_quality_signal(df: pd.DataFrame, signal_code: str) -> pd.Series:
    """Build a selection mask for the Overview quality-signal chart."""
    normalized_code = signal_code.strip().upper()
    signal_masks = _overview_quality_signal_masks(df)
    return signal_masks.get(normalized_code, pd.Series(False, index=df.index))


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


def _priority_cell_style(value: object) -> str | None:
    """Return CSS for a tinted priority cell in the issue list."""
    color_key = _priority_color_key(value)
    if color_key is None:
        return None

    palette = get_palette()
    background = palette.get(color_key)
    if not background:
        return None

    return (
        f"background-color: {with_alpha(background, 0.16)}; "
        f"color: {background}; "
        "font-weight: 700;"
    )


def _selection_mask_for_value(df: pd.DataFrame, value: str) -> pd.Series:
    """Build a chart-selection mask against the overview DataFrame."""
    normalized_value = value.strip()
    priority_text = df["priority"].astype(object).astype(str).str.strip().str.lower()
    priority_mask = priority_text == normalized_value.lower()
    if normalized_value.lower() == "unset":
        priority_mask = priority_mask | priority_text.isin(
            ["none", "nan", "<na>", ""]
        )

    assignee_mask = normalize_assignee_labels(df["assignee"]).str.contains(
        normalized_value, case=False, na=False
    )

    return (
        df["stage"].astype(str).str.contains(normalized_value, case=False, na=False)
        | assignee_mask
        | priority_mask
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
        "notes": _normalize_local_issue_notes(row.get("notes")),
    }


def _normalize_local_issue_notes(raw_notes: object) -> list[_IssueNoteData]:
    """Normalize seeded local-issue notes from parquet into dialog note records."""
    if raw_notes is None:
        return []

    values = raw_notes.tolist() if hasattr(raw_notes, "tolist") else raw_notes
    if isinstance(values, dict):
        values = [values]
    if not isinstance(values, list | tuple):
        return []

    notes: list[_IssueNoteData] = []
    for value in values:
        if not isinstance(value, dict):
            continue
        notes.append(
            {
                "author_name": str(value.get("author_name") or ""),
                "author_username": str(value.get("author_username") or ""),
                "body": str(value.get("body") or ""),
                "created_at": str(value.get("created_at") or ""),
                "system": bool(value.get("system", False)),
            }
        )

    return notes


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


def _normalize_issue_labels(raw_labels: object) -> list[str]:
    """Normalize labels from parquet/array/string forms into individual values."""
    if raw_labels is None:
        return []

    def _clean_labels(values: list[object]) -> list[str]:
        return [
            str(value).strip()
            for value in values
            if str(value).strip().lower() not in ("", "nan", "none", "<na>")
        ]

    if isinstance(raw_labels, list):
        return _clean_labels(raw_labels)

    raw = str(raw_labels).strip()
    if raw.lower() in ("", "nan", "none", "[]", "<na>"):
        return []

    try:
        parsed = ast.literal_eval(raw)
    except (ValueError, SyntaxError):
        parsed = None

    quoted_values = re.findall(r"'([^']+)'|\"([^\"]+)\"", raw)
    if len(quoted_values) > 1:
        return _clean_labels([first or second for first, second in quoted_values])

    if isinstance(parsed, list):
        return _clean_labels(parsed)

    if isinstance(parsed, tuple):
        return _clean_labels(list(parsed))

    return [raw]


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


def _build_issue_search_mask(
    df: pd.DataFrame,
    query: str,
    search_columns: tuple[str, ...] = _ISSUE_GRID_SEARCH_COLUMNS,
) -> pd.Series:
    """Build a fuzzy search mask across the filtered-issues table columns."""
    normalized_query = _normalize_issue_search_text(query)
    if not normalized_query:
        return pd.Series(True, index=df.index)

    active_columns = [column for column in search_columns if column in df.columns]
    if not active_columns:
        return pd.Series(True, index=df.index)

    searchable_df = df[active_columns].apply(lambda column: column.map(_normalize_issue_search_text))
    row_text = searchable_df.agg(" ".join, axis=1).str.replace(r"\s+", " ", regex=True).str.strip()
    query_tokens = normalized_query.split()

    token_mask = pd.Series(True, index=df.index)
    for token in query_tokens:
        token_mask &= row_text.str.contains(re.escape(token), case=False, na=False, regex=True)

    # Short-circuit: skip expensive fuzzy search when exact token matching
    # already found results.  Fuzzy matching is preserved as a fallback when
    # no exact matches exist (i.e. the user mistyped a query).
    if token_mask.any():
        return token_mask

    threshold = _issue_search_threshold(normalized_query)
    fuzzy_cell_mask = searchable_df.apply(
        lambda column: column.map(
            lambda value: _is_fuzzy_issue_search_match(value, normalized_query, threshold)
        )
    ).any(axis=1)

    return fuzzy_cell_mask


def _normalize_issue_search_text(value: object) -> str:
    """Normalize a cell value into plain lowercase text for issue-grid search."""
    if isinstance(value, dict):
        return " ".join(
            normalized
            for normalized in (_normalize_issue_search_text(item) for item in value.values())
            if normalized
        )
    if isinstance(value, (list, tuple, set)):
        return " ".join(
            normalized
            for normalized in (_normalize_issue_search_text(item) for item in value)
            if normalized
        )
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except TypeError:
        pass

    text = str(value).replace("_", " ").replace("::", " ")
    return re.sub(r"\s+", " ", text).strip().lower()


def _is_fuzzy_issue_search_match(value: str, normalized_query: str, threshold: float) -> bool:
    """Return whether a normalized cell value is a close fuzzy match."""
    if not value:
        return False
    if normalized_query in value:
        return True

    token_scores = [
        SequenceMatcher(None, normalized_query, token).ratio()
        for token in value.split()
    ]
    best_score = max([SequenceMatcher(None, normalized_query, value).ratio(), *token_scores])
    return best_score >= threshold


def _issue_search_threshold(normalized_query: str) -> float:
    """Return a typo-tolerant search threshold based on query length."""
    query_length = len(normalized_query)
    if query_length <= 4:
        return 0.9
    if query_length <= 8:
        return 0.82
    return 0.72


class IssueFacets(TypedDict, total=False):
    """Active issue-board filter, from the summary pills, the lane headers, the
    Analytics charts and the search panel.

    Every key is optional. ``state`` is ``opened``, ``closed`` or ``all`` (no
    state filter). ``priority`` is a priority label ("Unset" for issues without
    one). ``signal`` is a quality-signal code. ``query`` is free search text. ``recent``
    (``created`` or ``closed``) keeps the issues created, or closed, in the
    last ``RECENT_DAYS`` days. ``day`` (an ISO date) with ``day_kind``
    (``created`` or ``closed``) keeps the issues created, or closed, that day.
    """

    stage: str
    state: str
    priority: str
    signal: str
    query: str
    recent: str
    day: str
    day_kind: str


FACET_QUERY_PREFIX = "f_"
# ``customdata[0]`` of a priority donut's centre (``priority_donut.ALL_ISSUES``).
DONUT_ALL_ISSUES = "__all__"
_FACET_KEYS = ("stage", "state", "priority", "signal", "query", "recent", "day", "day_kind")
RECENT_DAYS = 7
_FACET_STATES = ("opened", "closed", "all")
_RECENT_KINDS = ("created", "closed")


def _clean_facets(raw: Mapping[str, object]) -> IssueFacets:
    """Keep only well-formed facet values."""
    values = {
        key: str(raw[key]).strip()
        for key in _FACET_KEYS
        if raw.get(key) is not None and str(raw[key]).strip()
    }
    if values.get("state") not in _FACET_STATES:
        values.pop("state", None)
    if values.get("recent") not in _RECENT_KINDS:
        values.pop("recent", None)
    if "day" in values:
        parsed_day = pd.to_datetime(values["day"], errors="coerce")
        if pd.isna(parsed_day) or values.get("day_kind") not in _RECENT_KINDS:
            values.pop("day")
        else:
            values["day"] = parsed_day.strftime("%Y-%m-%d")
    if "day" not in values:
        values.pop("day_kind", None)

    facets: IssueFacets = {}
    facets.update(values)  # type: ignore[typeddict-item]
    return facets


def recent_mask(df: pd.DataFrame, kind: str, now: pd.Timestamp | None = None) -> pd.Series:
    """Select issues created (or closed) in the last ``RECENT_DAYS`` days.

    The window covers today and the six days before it. Closed issues must
    also be in state ``closed``.
    """
    column = "closed_at" if kind == "closed" else "created_at"
    if column not in df.columns:
        return pd.Series(False, index=df.index)
    today = (now or pd.Timestamp.now(tz="UTC")).tz_convert("UTC").floor("D")
    start = today - pd.Timedelta(days=RECENT_DAYS - 1)
    dates = pd.to_datetime(df[column], errors="coerce", utc=True)
    mask = dates >= start
    if kind == "closed" and "state" in df.columns:
        mask &= df["state"] == "closed"
    return mask.fillna(False)


def facets_from_selection(
    chart_id: str,
    points: list[dict[str, object]],
    stage_filter: str | None = None,
    state_filter: str | None = None,
) -> IssueFacets:
    """Translate a Plotly selection in an Analytics chart into board facets.

    Args:
        chart_id: ``open_donut``, ``closed_donut``, ``velocity_chart``,
            ``issue_state_chart``, ``quality_signal_chart``, or a workflow-state
            bar chart (``stage_bar_<n>``).
        points: Selected points as reported by ``st.plotly_chart``.
        stage_filter: Stage the chart is scoped to, if any.
        state_filter: Issue state the chart is scoped to, if any.

    Returns:
        The facets the selection stands for; empty when nothing can be derived.
    """
    raw: dict[str, object] = {}
    if stage_filter:
        raw["stage"] = stage_filter
    if state_filter:
        raw["state"] = state_filter

    point = points[0] if points else {}
    value = point.get("label") or point.get("x") or point.get("y") or point.get("text")
    customdata = point.get("customdata")
    first_custom = (
        str(customdata[0]).strip() if isinstance(customdata, list) and customdata else ""
    )

    if chart_id in ("open_donut", "closed_donut"):
        # Donut slices carry their priority in ``customdata``; the centre
        # stands for all issues of the donut's state.
        if first_custom and first_custom != DONUT_ALL_ISSUES:
            raw["priority"] = first_custom
    elif isinstance(value, str) and value:
        if chart_id == "velocity_chart":
            is_closed = point.get("curveNumber") == 1
            if first_custom:
                is_closed = first_custom == "Closed"
            raw["day"] = value
            raw["day_kind"] = "closed" if is_closed else "created"
            # The line counts issues created that are still open, and issues
            # closed that day.
            raw["state"] = "closed" if is_closed else "opened"
        elif chart_id == "issue_state_chart":
            normalized = first_custom.lower() or value.strip().lower()
            if normalized in ("opened", "closed"):
                raw["state"] = normalized
            elif "open" in normalized:
                raw["state"] = "opened"
            elif "closed" in normalized:
                raw["state"] = "closed"
        elif chart_id == "quality_signal_chart":
            raw["signal"] = first_custom.upper() or value.strip().upper().replace(" ", "_")
        else:
            raw["priority"] = value.replace("<b>", "").replace("</b>", "").strip()

    return _clean_facets(raw)


def filter_issues(df: pd.DataFrame, facets: IssueFacets) -> pd.DataFrame:
    """Return the issues matching every active facet."""
    result = df
    if "stage" in facets:
        result = result[result["stage"] == facets["stage"]]
    if facets.get("state") in ("opened", "closed"):
        result = result[result["state"] == facets["state"]]
    if "recent" in facets:
        result = result[recent_mask(result, facets["recent"])]
    if "day" in facets:
        column = "closed_at" if facets.get("day_kind") == "closed" else "created_at"
        if column in result.columns:
            dates = pd.to_datetime(result[column], errors="coerce", utc=True)
            result = result[dates.dt.strftime("%Y-%m-%d") == facets["day"]]
    if "signal" in facets:
        result = result[_selection_mask_for_quality_signal(result, facets["signal"])]
    if "priority" in facets:
        result = result[_selection_mask_for_value(result, facets["priority"])]
    if "query" in facets and not result.empty:
        searchable = result.assign(
            priority=result["priority"].astype(object).fillna("Unset")
        )
        result = result[_build_issue_search_mask(searchable, facets["query"])]
    return result


def facet_chips(facets: IssueFacets) -> list[tuple[str, str]]:
    """Return ``(facet key, display label)`` pairs for the active facets."""
    chips: list[tuple[str, str]] = []
    if "stage" in facets:
        chips.append(("stage", f"Stage: {facets['stage']}"))
    if facets.get("state") in ("closed", "all") and not {"recent", "day"} & set(facets):
        # Open issues are the default, so an "opened" state needs no chip; a
        # last-7-days or single-day facet already says which issues it covers.
        state_label = "Closed" if facets["state"] == "closed" else "All"
        chips.append(("state", f"State: {state_label}"))
    if "priority" in facets:
        chips.append(("priority", f"Priority: {facets['priority']}"))
    if "signal" in facets:
        signal_label = facets["signal"].replace("_", " ").title()
        chips.append(("signal", f"Signal: {signal_label}"))
    if "recent" in facets:
        kind = "Closed" if facets["recent"] == "closed" else "Created"
        chips.append(("recent", f"{kind}: last {RECENT_DAYS} days"))
    if "day" in facets:
        kind = "Closed" if facets.get("day_kind") == "closed" else "Created"
        chips.append(("day", f"{kind}: {pd.Timestamp(facets['day']).strftime('%b %d, %Y')}"))
    if "query" in facets:
        chips.append(("query", f"Search: {facets['query']}"))
    return chips


def without_facet(facets: IssueFacets, key: str) -> IssueFacets:
    """Return the facets with one chip removed."""
    remaining = {name: value for name, value in facets.items() if name != key}
    if key == "day":
        remaining.pop("day_kind", None)
    return _clean_facets(remaining)


def facets_to_query(facets: IssueFacets) -> dict[str, str]:
    """Serialize facets into URL query parameters."""
    return {f"{FACET_QUERY_PREFIX}{key}": str(value) for key, value in facets.items()}


def facets_from_query(params: Mapping[str, object]) -> IssueFacets:
    """Parse facets from URL query parameters, ignoring malformed values."""
    return _clean_facets(
        {
            key: params[f"{FACET_QUERY_PREFIX}{key}"]
            for key in _FACET_KEYS
            if f"{FACET_QUERY_PREFIX}{key}" in params
        }
    )


def collapse_issue_contexts(df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per issue, with ``context`` holding every context label."""
    if "id" not in df.columns:
        return df
    unique = df.drop_duplicates(subset=["id"]).copy()
    if "context" not in df.columns:
        return unique
    context_frame = pd.DataFrame(
        {"id": df["id"], "context": df["context"].astype(object)}
    ).dropna(subset=["context"])
    context_lists = context_frame.groupby("id")["context"].agg(
        lambda values: list(dict.fromkeys(values))
    )
    unique["context"] = unique["id"].map(context_lists).map(
        lambda value: value if isinstance(value, list) else []
    )
    return unique


_DEFAULT_STAGE_ORDER = (
    "Backlog",
    "To Do",
    "In Progress",
    "Review",
    "Testing",
    "Waiting for Release",
    "Done",
    "Closed",
)


def _ordered_stages(df: pd.DataFrame) -> list[str]:
    """Return the stages present in ``df`` in workflow order."""
    if df.empty or "stage" not in df.columns:
        return []
    if "stage_order" in df.columns:
        order = df.groupby("stage", observed=True)["stage_order"].min()
        return [str(stage) for stage in order.sort_values(kind="stable").index]
    stages = [str(stage) for stage in df["stage"].dropna().unique()]
    return sorted(
        stages,
        key=lambda stage: (
            _DEFAULT_STAGE_ORDER.index(stage)
            if stage in _DEFAULT_STAGE_ORDER
            else len(_DEFAULT_STAGE_ORDER)
        ),
    )


def overview_stages(df: pd.DataFrame) -> list[str]:
    """Return the stages of the workflow-state chart: stages with open issues."""
    if "state" not in df.columns:
        return _ordered_stages(df)
    return _ordered_stages(df[df["state"] == "opened"])


def board_lanes(chart_stages: list[str], issues: pd.DataFrame) -> list[str]:
    """Return the board lanes for these issues, aligned with the stage chart.

    The lanes start with the chart's stages, empty ones included, so each lane
    sits under its chart column. Stages the chart does not show (for example
    "Done" for closed issues) are appended. When none of the issues is in a
    chart stage, only the stages that have issues are shown.
    """
    present = _ordered_stages(issues)
    lanes = list(chart_stages) if any(stage in chart_stages for stage in present) else []
    return lanes + [stage for stage in present if stage not in lanes]


def priority_labels(df: pd.DataFrame) -> pd.Series:
    """Return each issue's priority label; missing priorities become "Unset"."""
    priority = df["priority"].astype(object)
    text = priority.astype(str).str.strip()
    unset = priority.isna() | text.str.lower().isin(["", "none", "nan", "<na>"])
    return text.where(~unset, "Unset")


def lane_priority_counts(issues: pd.DataFrame) -> dict[str, list[tuple[str, int]]]:
    """Count issues per stage and priority, priorities in rank order, "Unset" last.

    Args:
        issues: One row per issue, with ``stage`` and ``priority``.

    Returns:
        ``{stage: [(priority label, count), ...]}``.
    """
    if issues.empty or "stage" not in issues.columns:
        return {}
    ranks = (
        pd.to_numeric(issues["priority_rank"], errors="coerce")
        if "priority_rank" in issues.columns
        else pd.Series(float("nan"), index=issues.index)
    )
    frame = pd.DataFrame(
        {"stage": issues["stage"].astype(str), "priority": priority_labels(issues), "rank": ranks}
    )
    counts = (
        frame.groupby(["stage", "priority"])
        .agg(count=("priority", "size"), rank=("rank", "min"))
        .reset_index()
    )
    counts["unset"] = counts["priority"] == "Unset"
    counts = counts.sort_values(["stage", "unset", "rank", "priority"], na_position="last")
    return {
        str(stage): list(zip(group["priority"], group["count"].astype(int), strict=True))
        for stage, group in counts.groupby("stage", sort=False)
    }


# Streamlit text colours for priority dots, most urgent first; "Unset" is gray.
_PRIORITY_COLOR_NAMES = ("red", "orange", "green", "blue", "violet")


def priority_color_names(df: pd.DataFrame) -> dict[str, str]:
    """Map each priority label to a Streamlit text colour, by ``priority_rank``.

    The same priority gets the same dot colour in the summary pills and in
    every lane header.
    """
    if df.empty or "priority" not in df.columns:
        return {"Unset": "gray"}
    ranks = (
        pd.to_numeric(df["priority_rank"], errors="coerce")
        if "priority_rank" in df.columns
        else pd.Series(float("nan"), index=df.index)
    )
    order = (
        pd.DataFrame({"label": priority_labels(df), "rank": ranks})
        .groupby("label")["rank"]
        .min()
        .reset_index()
    )
    order = order[order["label"] != "Unset"].sort_values(["rank", "label"], na_position="last")
    colors = {
        str(label): _PRIORITY_COLOR_NAMES[min(position, len(_PRIORITY_COLOR_NAMES) - 1)]
        for position, label in enumerate(order["label"])
    }
    colors["Unset"] = "gray"
    return colors
