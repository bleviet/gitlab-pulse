"""Capacity & Risk View for Layer 3 Dashboard.

Visualizes workload distribution, context switching risks, and latent work.
Refactored to use Widget Registry where applicable.
"""

import hashlib
import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.utils import get_semantic_color
from app.dashboard.widgets import tables
from app.dashboard.components import style_metric_cards


def render_capacity_view(
    df: pd.DataFrame,
    colors: dict[str, str] | None = None,
    capacity_config: dict | None = None
) -> None:
    """Render the Capacity & Risk page.

    Args:
        df: Filtered DataFrame with valid issues
        colors: Optional dictionary of semantic colors to override defaults
        capacity_config: Configuration dictionary for capacity limits and privacy
    """
    st.header("⚖️ Risk & Capacity")
    st.caption("Identify bottlenecks, overload, and context-switching risks.")

    # Apply Bento Grid Style
    style_metric_cards()

    if df.empty:
        st.warning("No data available.")
        return

    # Configuration Defaults
    config = capacity_config or {}
    max_wip = config.get("max_wip_per_person", 5)
    max_contexts = config.get("max_contexts_per_person", 2)
    anonymize = config.get("anonymize_users", False)
    hidden_users = set(config.get("hidden_users", []))

    # --- Data Preparation ---
    work_df = df[
        (df["stage_type"].isin(["active", "waiting"])) &
        (df["state"] == "opened")
    ].copy()

    if work_df.empty:
        st.info("No active work found.")
        return

    # Normalize Assignee
    work_df["assignee"] = work_df["assignee"].fillna("Unassigned")

    # Filter Hidden Users
    if hidden_users:
        work_df = work_df[~work_df["assignee"].isin(hidden_users)]

    # Anonymization Logic
    if anonymize:
        def hash_user(name: str) -> str:
            if name == "Unassigned":
                return name
            h = hashlib.md5(name.encode()).hexdigest()[:4]
            return f"User-{h}"
        work_df["assignee"] = work_df["assignee"].apply(hash_user)

    # --- Visualizations ---
    risk_views = {
        "🏋️ Workload Balancer": "workload",
        "🔀 Context Switching": "context",
        "⚠️ Unassigned Risk": "unassigned"
    }

    selected_view_label = st.radio(
        "Risk View",
        options=list(risk_views.keys()),
        horizontal=True,
        label_visibility="collapsed",
        key="capacity_risk_view_radio"
    )

    selected_view = risk_views[selected_view_label]
    active_filters = []

    if selected_view == "workload":
        with st.expander("📊 Workload Distribution", expanded=True):
            sel = _render_workload_chart(work_df, colors, max_wip)
        if sel:
            active_filters.extend(sel)

    elif selected_view == "context":
        sel = _render_context_matrix(work_df, max_contexts)
        if sel:
            active_filters.extend(sel)

    elif selected_view == "unassigned":
        _render_unassigned_risk(work_df)

    # --- Filter Logic ---
    display_df = work_df
    grid_msg = "Active Inventory"

    if active_filters:
        mask = pd.Series(False, index=display_df.index)
        for f in active_filters:
            criteria_mask = (display_df["assignee"] == f["assignee"])
            if f.get("stage"):
                criteria_mask &= (display_df["stage"] == f["stage"])
            if f.get("context"):
                criteria_mask &= (display_df["context"] == f["context"])
            mask |= criteria_mask
        grid_df = display_df[mask]
        grid_msg = f"Filtered ({len(grid_df)} items)"
    else:
        grid_df = display_df

    # --- Detailed Grid ---
    with st.expander(f"📋 {grid_msg}", expanded=True):
        _render_capacity_grid(grid_df)


def _render_workload_chart(df: pd.DataFrame, colors: dict[str, str] | None, threshold: int) -> list[dict] | None:
    """Render Stacked Bar Chart of Assignee vs Issue Count.

    Returns:
        List of selected points [{'assignee': '...', 'stage': '...'}] if any.
    """
    stage_order_map = df.groupby("stage")["stage_order"].min()
    df["stage_order"] = df["stage"].map(stage_order_map)
    df = df.sort_values("stage_order")

    load_counts = df.groupby(["assignee", "stage", "stage_type"]).size().reset_index(name="count")

    total_load = load_counts.groupby("assignee")["count"].sum().sort_values(ascending=False)
    sorted_assignees = total_load.index.tolist()

    if load_counts.empty:
        st.info("No active workload.")
        return None

    overloaded = total_load[total_load > threshold]
    if not overloaded.empty:
        st.warning(f"⚠️ High Load Detected: {len(overloaded)} people have > {threshold} items.")

    fig = px.bar(
        load_counts,
        x="assignee",
        y="count",
        color="stage",
        title="",
        category_orders={"assignee": sorted_assignees},
        custom_data=["stage"],
    )

    fig.add_hline(y=threshold, line_dash="dash", line_color="red", annotation_text=f"Limit ({threshold})")

    fig.update_layout(
        xaxis_title="Assignee",
        yaxis_title="Item Count",
        legend_title="Stage",
        height=500,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif"),
        yaxis=dict(showgrid=True, gridcolor="rgba(128, 128, 128, 0.2)"),
        xaxis=dict(showgrid=False),
    )

    event = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        selection_mode=["points"]
    )

    if event and event.selection and event.selection.points:
        return [
            {"assignee": p["x"], "stage": p["customdata"][0]}
            for p in event.selection.points
        ]

    return None


def _render_context_matrix(df: pd.DataFrame, threshold: int) -> list[dict] | None:
    """Render Heatmap of Assignee vs Context.

    Returns:
        List of selected points [{'assignee': '...', 'context': '...'}] if any.
    """
    st.subheader("Context Switching Matrix")

    if "context" not in df.columns:
        st.info("No context data available.")
        return None

    matrix = df.groupby(["assignee", "context"]).size().reset_index(name="count")
    context_counts = df.groupby("assignee")["context"].nunique().sort_values(ascending=False)
    sorted_assignees = context_counts.index.tolist()

    risky_people = context_counts[context_counts > threshold]
    if not risky_people.empty:
        st.warning(f"⚠️ Fragmented Attention: {len(risky_people)} people match > {threshold} contexts.")

    fig = px.density_heatmap(
        matrix,
        x="context",
        y="assignee",
        z="count",
        category_orders={"assignee": sorted_assignees},
        color_continuous_scale="Viridis",
        text_auto=True
    )

    fig.update_layout(
        xaxis_title="Context",
        yaxis_title="Assignee",
        height=500,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif"),
    )

    event = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        selection_mode=["points"]
    )

    if event and event.selection and event.selection.points:
        return [
            {"assignee": p["y"], "context": p["x"]}
            for p in event.selection.points
        ]

    return None


def _render_unassigned_risk(df: pd.DataFrame) -> None:
    """Render details about Unassigned work."""
    st.subheader("Latent Work (Unassigned)")

    unassigned = df[df["assignee"] == "Unassigned"]
    count = len(unassigned)

    st.metric("Unassigned Active Items", count)

    if count > 0:
        st.markdown(f"**{count} items** are in active stages but have no owner. This creates hidden queues.")
        breakdown = unassigned["stage"].value_counts().reset_index()
        breakdown.columns = ["Stage", "Count"]
        st.dataframe(breakdown, hide_index=True)


def _render_capacity_grid(df: pd.DataFrame) -> None:
    """Render filterable grid of active work."""
    with st.expander("🔍 Filters", expanded=False):
        title_search = st.text_input(
            "Search Title",
            placeholder="Type to search issue titles...",
            key="cap_filter_title"
        )

        filter_cols = st.columns(3)

        with filter_cols[0]:
            if "assignee" in df.columns:
                available_assignees = sorted(df["assignee"].dropna().unique().tolist())
                selected_assignees = st.multiselect(
                    "Assignee",
                    options=available_assignees,
                    default=[],
                    key="cap_filter_assignee"
                )
            else:
                selected_assignees = []

        with filter_cols[1]:
            if "priority" in df.columns:
                available_priorities = sorted(df["priority"].dropna().unique().tolist())
                selected_priorities = st.multiselect(
                    "Priority",
                    options=available_priorities,
                    default=[],
                    key="cap_filter_priority"
                )
            elif "severity" in df.columns:
                available_priorities = sorted(df["severity"].dropna().unique().tolist())
                selected_priorities = st.multiselect(
                    "Priority (Severity)",
                    options=available_priorities,
                    default=[],
                    key="cap_filter_priority"
                )
            else:
                selected_priorities = []

        with filter_cols[2]:
            if "milestone" in df.columns:
                available_milestones = sorted(df["milestone"].dropna().unique().tolist())
                selected_milestones = st.multiselect(
                    "Milestone",
                    options=available_milestones,
                    default=[],
                    key="cap_filter_milestone"
                )
            else:
                selected_milestones = []

    display_df = df.copy()

    if title_search:
        display_df = display_df[display_df["title"].str.contains(title_search, case=False, na=False)]
    if selected_assignees:
        display_df = display_df[display_df["assignee"].isin(selected_assignees)]
    if selected_priorities:
        priority_col = "priority" if "priority" in display_df.columns else "severity"
        display_df = display_df[display_df[priority_col].isin(selected_priorities)]
    if selected_milestones:
        display_df = display_df[display_df["milestone"].isin(selected_milestones)]

    cols_to_show = ["web_url", "assignee", "title", "stage", "priority", "milestone", "days_in_stage", "context", "weight"]
    available_cols = [c for c in cols_to_show if c in display_df.columns]

    display_df = display_df[available_cols].sort_values(["assignee", "days_in_stage"], ascending=[True, False])

    st.dataframe(
        display_df,
        width="stretch",
        height=800,
        hide_index=True,
        column_config={
            "web_url": st.column_config.LinkColumn(
                "IID",
                display_text=r"/(?:issues|work_items)/(\d+)$",
                width="small",
                help="Click to open in GitLab"
            ),
            "assignee": st.column_config.TextColumn("Assignee"),
            "days_in_stage": st.column_config.NumberColumn("Age (Days)", format="%d"),
            "weight": st.column_config.NumberColumn("Weight"),
            "priority": st.column_config.TextColumn("Priority"),
            "milestone": st.column_config.TextColumn("Milestone"),
        }
    )
