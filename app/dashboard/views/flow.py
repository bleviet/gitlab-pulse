"""Flow Page (Value Stream) for Layer 3 Dashboard.

Visualizes flow efficiency, bottlenecks, and aging.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Semantic color palette
COLORS = {
    "primary": "#4F46E5",
    "active": "#3B82F6",
    "waiting": "#F59E0B",
    "completed": "#10B981",
    "neutral": "#64748B",
}


def render_flow_view(df: pd.DataFrame) -> None:
    """Render the Flow (Value Stream) page.

    Args:
        df: Filtered DataFrame with valid issues
    """
    st.header("🌊 Development Value Stream")
    st.caption("Flow metrics: Inventory, Staleness, and Efficiency")

    # Filter out empty stages or irrelevant data if needed
    # But for flow, we usually want to see everything
    if df.empty:
        st.warning("No data available.")
        return

    # Top Row: Metrics
    _render_flow_metrics(df)

    st.divider()

    # Main columns
    col1, col2 = st.columns(2)

    with col1:
        _render_funnel_chart(df)

    with col2:
        _render_aging_chart(df)

    st.divider()

    # Detail grid (Drill-down)
    _render_issue_detail_grid(df)


def _render_flow_metrics(df: pd.DataFrame) -> None:
    """Render Flow key metrics."""
    col1, col2, col3, col4 = st.columns(4)

    # 1. Active WIP
    active_mask = df["stage_type"] == "active"
    active_count = len(df[active_mask])
    
    with col1:
        st.metric("Active WIP", active_count, help="Issues in active stages")

    # 2. Flow Efficiency
    total_wip = len(df[df["stage_type"].isin(["active", "waiting"])])
    if total_wip > 0:
        efficiency = round((active_count / total_wip) * 100, 1)
    else:
        efficiency = 0

    with col2:
        st.metric(
            "Flow Efficiency", 
            f"{efficiency}%", 
            help="Active / (Active + Waiting)"
        )

    # 3. Bottleneck (Max WIP Stage that is NOT Done)
    # Exclude 'completed' stage types usually for bottleneck analysis
    wip_df = df[df["stage_type"] != "completed"]
    if not wip_df.empty:
        stage_counts = wip_df["stage"].value_counts()
        bottleneck_stage = stage_counts.idxmax()
        bottleneck_count = stage_counts.max()
    else:
        bottleneck_stage = "None"
        bottleneck_count = 0

    with col3:
        st.metric("Top Bottleneck", bottleneck_stage, f"{bottleneck_count} items")

    # 4. Max Staleness
    max_days = df["days_in_stage"].max() if not df.empty else 0
    with col4:
        st.metric("Max Staleness", f"{max_days} days", help="Longest time in current stage")


def _render_funnel_chart(df: pd.DataFrame) -> None:
    """Render horizontal bar chart of issues per stage (The Funnel)."""
    st.subheader("🔻 Project Funnel (WIP)")
    
    # Aggregation
    stage_stats = df.groupby(["stage", "stage_order"]).size().reset_index(name="count")
    
    # Sort by defined order
    stage_stats = stage_stats.sort_values("stage_order")
    
    if stage_stats.empty:
        st.info("No stage data.")
        return

    fig = px.bar(
        stage_stats,
        x="count",
        y="stage",
        orientation="h",
        text="count",
        title="",
    )

    fig.update_traces(marker_color=COLORS["primary"], textposition="auto")
    
    fig.update_layout(
        height=400,
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(autorange="reversed"), # Top to bottom flow
        xaxis=dict(showgrid=True, gridcolor="rgba(100,116,139,0.2)"),
    )

    st.plotly_chart(fig, width="stretch")


def _render_aging_chart(df: pd.DataFrame) -> None:
    """Render boxplot of days in stage."""
    st.subheader("⏳ Stage Stickiness (Aging)")

    # Filter out completed if we want to focus on WIP aging? 
    # Usually we want to see aging of current items.
    
    # Sort stages by order for x-axis
    df_sorted = df.sort_values("stage_order")

    if df_sorted.empty:
        st.info("No data.")
        return

    fig = px.box(
        df_sorted,
        x="stage",
        y="days_in_stage",
        color="stage_type",
        color_discrete_map={
            "active": COLORS["active"],
            "waiting": COLORS["waiting"],
            "completed": COLORS["completed"],
            "active": COLORS["active"], # Duplicate key? No, just ensuring
        },
        points="outliers", # Show outliers
    )

    fig.update_layout(
        height=400,
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(showgrid=True, gridcolor="rgba(100,116,139,0.2)", title="Days in Stage"),
        xaxis=dict(title=None),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    st.plotly_chart(fig, width="stretch")


def _render_issue_detail_grid(df: pd.DataFrame) -> None:
    """Render unified issue detail grid with drill-down filters."""
    st.subheader("📋 Issue Drill-down")
    st.caption("Inspect issues by stage.")

    # 1. Multi-select Filter
    available_stages = sorted(df["stage"].unique(), key=lambda s: df[df["stage"] == s]["stage_order"].min())
    selected_stages = st.multiselect(
        "Filter by Stage",
        options=available_stages,
        default=[],
        help="Select stages to drill down into specifics."
    )

    # 2. Filter Data
    if selected_stages:
        display_df = df[df["stage"].isin(selected_stages)].copy()
    else:
        display_df = df.copy()

    # 3. Sort by Age (Staleness focus)
    display_df = display_df.sort_values("days_in_stage", ascending=False)

    # 4. Select Columns
    cols_to_show = [
        "iid", "title", "stage", "days_in_stage", "assignee", "web_url"
    ]
    # Filter columns that exist
    cols = [c for c in cols_to_show if c in display_df.columns]
    
    # Rename for display
    display_df = display_df[cols].rename(columns={
        "days_in_stage": "Days in Stage",
        "stage": "Stage",
        "title": "Title",
        "assignee": "Assignee",
        "iid": "IID",
    })

    # 5. Render Dataframe with Links
    st.dataframe(
        display_df,
        column_config={
            "web_url": st.column_config.LinkColumn("GitLab Link"),
            "Days in Stage": st.column_config.NumberColumn(
                "Days in Stage",
                help="Days since last update in this stage",
                format="%d days",
            ),
        },
        width="stretch",
        hide_index=True,
    )
