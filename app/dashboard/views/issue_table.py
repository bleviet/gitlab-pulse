"""Issue table of the Overview's issue panel.

Shapes the filtered issues into table rows and renders one page of them; the
page bar (``issue_pages``) is rendered by the panel, above the table.
"""

import pandas as pd
import streamlit as st

from app.dashboard.data_loader import load_labels
from app.dashboard.utils import sort_hierarchy
from app.dashboard.views.issue_data import (
    IssueFacets,
    _issue_quality_hints_text,
    _priority_cell_style,
)
from app.dashboard.views.issue_pages import PageWindow
from app.dashboard.widgets import tables


def prepare_issue_rows(issues: pd.DataFrame) -> pd.DataFrame:
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
    rows = rows.reset_index(drop=True)
    rows["title"] = (
        rows["web_url"].astype(str)
        + "#"
        + rows["iid"].astype(str)
        + " - "
        + rows["title"].fillna("")
    )
    return rows


def render_issue_table(
    rows: pd.DataFrame, facets: IssueFacets, page: PageWindow
) -> None:
    """Render the issue table; the title links to the issue in GitLab.

    Args:
        rows: The prepared rows of every matching issue (``prepare_issue_rows``).
        facets: The active facets; the stage column is hidden while one is set.
        page: The slice of ``rows`` to show, from the page bar.
    """
    rows = rows.iloc[page.start:page.stop]
    rows = rows.assign(quality_hints=rows.apply(_issue_quality_hints_text, axis=1))

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
        "on_select": "ignore",
        "key": "issue_table",
        "minimize_columns": False,
        "enable_filters": False,
    }
    tables.issue_detail_grid(
        rows.style.map(_priority_cell_style, subset=["priority"]), config=grid_config
    )
