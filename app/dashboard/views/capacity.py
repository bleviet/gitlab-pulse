"""Capacity & Risk View for Layer 3 Dashboard.

Visualizes workload distribution, context switching risks, and latent work.
"""

import hashlib
import pandas as pd
import plotly.express as px
import streamlit as st
import numpy as np

from app.dashboard.utils import get_semantic_color

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

    # 1. Filter for Active Work only (Inventory)
    # We care about what is currently on plates, not what is done.
    # Exclude 'completed' stage types.
    # Also exclude Backlog? Depends. Usually "Capacity" is about "Committed" work.
    # Let's keep Active and Waiting stages.
    
    # We use a copy to avoid mutating the global DF
    work_df = df[
        (df["stage_type"].isin(["active", "waiting"])) &
        (df["state"] == "opened")
    ].copy()

    if work_df.empty:
        st.info("No active work found.")
        return

    # 2. Normalize Assignee
    # Fill NaN with "Unassigned"
    work_df["assignee"] = work_df["assignee"].fillna("Unassigned")

    # 3. Filter Hidden Users
    if hidden_users:
        work_df = work_df[~work_df["assignee"].isin(hidden_users)]

    # 4. Anonymization Logic
    if anonymize:
        def hash_user(name: str) -> str:
            if name == "Unassigned":
                return name
            # Simple consistent hash
            h = hashlib.md5(name.encode()).hexdigest()[:4]
            return f"User-{h}"
        
        work_df["assignee"] = work_df["assignee"].apply(hash_user)

    # --- Visualizations ---

    # Tabbed layout for different risk perspectives
    tab1, tab2, tab3 = st.tabs(["🏋️ Workload Balancer", "🔀 Context Switching", "⚠️ Unassigned Risk"])

    with tab1:
        _render_workload_chart(work_df, colors, max_wip)
    
    with tab2:
        _render_context_matrix(work_df, max_contexts)
        
    with tab3:
        _render_unassigned_risk(work_df)

    # --- Detailed Grid ---
    with st.expander("📋 Active Inventory", expanded=True):
        _render_capacity_grid(work_df)


def _render_workload_chart(df: pd.DataFrame, colors: dict[str, str] | None, threshold: int) -> None:
    """Render Stacked Bar Chart of Assignee vs Issue Count."""
    st.subheader("Workload Distribution")
    
    # Aggregation: Assignee -> Stage -> Count
    # We want to stack by Stage to see *where* they are stuck
    
    # Ensure stages are ordered correctly
    stage_order_map = df.groupby("stage")["stage_order"].min()
    df["stage_order"] = df["stage"].map(stage_order_map)
    df = df.sort_values("stage_order")
    
    load_counts = df.groupby(["assignee", "stage", "stage_type"]).size().reset_index(name="count")
    
    # Order Assignees by total load (descending)
    total_load = load_counts.groupby("assignee")["count"].sum().sort_values(ascending=False)
    sorted_assignees = total_load.index.tolist()
    
    if load_counts.empty:
        st.info("No active workload.")
        return

    # Alert for threshold
    overloaded = total_load[total_load > threshold]
    if not overloaded.empty:
        st.warning(f"⚠️ High Load Detected: {len(overloaded)} people have > {threshold} items.")

    # Color mapping for stages
    # Use stage_type colors if specific stage colors aren't defined? 
    # Or just loop existing mapped colors.
    # Let's try to map stage_type to semantic colors if possible, or distinct colors.
    # Actually, using the stage name is better for detail, but we need consistent colors.
    # For now, let generic plotly handle it or map stage types.
    
    # Let's map stage names to colors if we have them, else fallback.
    # We can use the 'active', 'waiting' semantic mapping for the stage types.
    
    fig = px.bar(
        load_counts,
        x="assignee",
        y="count",
        color="stage",
        title="",
        category_orders={"assignee": sorted_assignees},
        # hover_data=["stage_type"],
    )
    
    fig.add_hline(y=threshold, line_dash="dash", line_color="red", annotation_text=f"Limit ({threshold})")

    fig.update_layout(
        xaxis_title="Assignee",
        yaxis_title="Item Count",
        legend_title="Stage",
        height=500
    )
    
    st.plotly_chart(fig, width="stretch")


def _render_context_matrix(df: pd.DataFrame, threshold: int) -> None:
    """Render Heatmap of Assignee vs Context."""
    st.subheader("Context Switching Matrix")
    
    if "context" not in df.columns:
        st.info("No context data available.")
        return
        
    # Pivot: Assignee x Context -> Count
    matrix = df.groupby(["assignee", "context"]).size().reset_index(name="count")
    
    # Calculate context count per person for sorting
    context_counts = df.groupby("assignee")["context"].nunique().sort_values(ascending=False)
    sorted_assignees = context_counts.index.tolist()
    
    # Check for risks
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
         height=500
    )
    
    st.plotly_chart(fig, width="stretch")


def _render_unassigned_risk(df: pd.DataFrame) -> None:
    """Render details about Unassigned work."""
    st.subheader("Latent Work (Unassigned)")
    
    unassigned = df[df["assignee"] == "Unassigned"]
    count = len(unassigned)
    
    st.metric("Unassigned Active Items", count)
    
    if count > 0:
        st.markdown(f"**{count} items** are in active stages but have no owner. This creates hidden queues.")
        
        # Show breakdown by stage
        breakdown = unassigned["stage"].value_counts().reset_index()
        breakdown.columns = ["Stage", "Count"]
        st.dataframe(breakdown, hide_index=True)


def _render_capacity_grid(df: pd.DataFrame) -> None:
    """Render filterable grid of active work."""
    # Simplified grid focused on Assignment and Age
    
    cols_to_show = ["assignee", "title", "stage", "days_in_stage", "context", "weight"]
    available_cols = [c for c in cols_to_show if c in df.columns]
    
    # Default Sort: Assignee then Age
    display_df = df[available_cols].sort_values(["assignee", "days_in_stage"], ascending=[True, False])
    
    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config={
            "assignee": st.column_config.TextColumn("Assignee"),
            "days_in_stage": st.column_config.NumberColumn("Age (Days)", format="%d"),
            "weight": st.column_config.NumberColumn("Weight"),
        }
    )
