"""Capacity & Risk View for Layer 3 Dashboard.

Visualizes workload distribution, context switching risks, and latent work.
Refactored to use Widget Registry where applicable.
"""

import hashlib
import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.utils import get_semantic_color
from app.dashboard.widgets import tables, charts
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
            sel = charts.workload_distribution(
                work_df, 
                config={
                    "threshold": max_wip, 
                    "key": "capacity_workload_chart"
                }
            )
        
        # Adapt selection
        if sel and sel.get("selection", {}).get("points"):
            points = sel["selection"]["points"]
            for p in points:
                # Horizontal bar: y is assignee
                f = {"assignee": p.get("y")}
                # Try to get stage from legendgroup (standard plotly express)
                if "legendgroup" in p:
                    f["stage"] = p["legendgroup"]
                active_filters.append(f)

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
            # Handle potential missing assignee if bad click
            if not f.get("assignee"):
                continue
                
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

    with st.expander(f"📋 {grid_msg}", expanded=True):
        tables.issue_detail_grid(
            grid_df, 
            config={
                "columns": ["web_url", "title", "assignee", "stage", "days_in_stage", "context", "weight"],
                "column_config": {
                    "Age (Days)": st.column_config.NumberColumn("Age", format="%d days"),
                }
            }
        )





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



