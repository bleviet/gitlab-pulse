"""Flow Page (Value Stream) for Layer 3 Dashboard.

Visualizes flow efficiency, bottlenecks, and aging.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.utils import sort_hierarchy

# Semantic color palette
COLORS = {
    "primary": "#4F46E5",
    "active": "#3B82F6",
    "waiting": "#F59E0B",
    "completed": "#10B981",
    "neutral": "#64748B",
}


def render_flow_view(df: pd.DataFrame, colors: dict[str, str] | None = None) -> None:
    """Render the Flow (Value Stream) page.

    Args:
        df: Filtered DataFrame with valid issues
        colors: Optional dictionary of semantic colors to override defaults
    """
    if colors:
        COLORS.update(colors)

    st.header("🌊 Development Value Stream")
    st.caption("Flow metrics: Inventory, Staleness, and Efficiency")

    # Filter out empty stages or irrelevant data if needed
    # But for flow, we usually want to see everything
    if df.empty:
        st.warning("No data available.")
        return

    # Top Row: Metrics
    _render_flow_metrics(df)

    # Charts (Collapsible)
    with st.expander("📊 Flow Charts", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            funnel_selection = _render_funnel_chart(df)
        with col2:
            aging_selection = _render_aging_chart(df)

    # Apply interactive filters
    filtered_df = df.copy()
    
    # Filter by Funnel Selection
    if funnel_selection and funnel_selection.get("selection", {}).get("points"):
        selected_points = funnel_selection["selection"]["points"]
        # Extract filters: stage and severity
        # We perform an OR filter for multiple selected points
        masks = []
        for point in selected_points:
            # Point has customdata or y (stage) and legend group/color (severity)
            # px.bar with orientation h: y is stage, color is severity
            # customdata is likely needed to be robust
            stage = point.get("y")
            severity = point.get("customdata", [None])[0] # customdata[0] is severity if we add it
            
            mask = (filtered_df["stage"] == stage)
            if severity:
                 # Normalize severity for comparison to match the chart's logic
                 # The chart uses Title Case for all severities, and "Unset" for NaNs
                 
                 if severity == "Unset":
                     # Match "Unset", NaNs, None, empty strings
                     mask &= (
                         filtered_df["severity"].isna() | 
                         (filtered_df["severity"].astype(str).str.strip().str.lower().isin(["unset", "none", "nan", "<na>", ""]))
                     )
                 else:
                     # Match severity (case-insensitive to be safe)
                     mask &= (filtered_df["severity"].astype(str).str.strip().str.lower() == severity.lower())
            
            masks.append(mask)
            
        if masks:
            final_mask = pd.Series(False, index=filtered_df.index)
            for m in masks:
                final_mask |= m
            filtered_df = filtered_df[final_mask]

    # Filter by Aging Selection (Intersection with Funnel)
    if aging_selection and aging_selection.get("selection", {}).get("points"):
        selected_points = aging_selection["selection"]["points"]
        # Aging chart: x=stage, y=days_in_stage, color=stage_type
        # We filter by stage (x). Days is continuous, so selecting a point usually implies interest in that item or stage.
        # But boxplots selection might be selecting outliers?
        # Let's assume selecting points filters by Stage of those points.
        selected_stages = {p.get("x") for p in selected_points}
        if selected_stages:
            filtered_df = filtered_df[filtered_df["stage"].isin(selected_stages)]

    # Detail grid (Collapsible)
    with st.expander("📋 Issue Details", expanded=True):
        _render_issue_detail_grid(filtered_df)


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



def _render_funnel_chart(df: pd.DataFrame) -> dict | None:
    """Render horizontal bar chart of issues per stage (The Funnel).
    
    Returns:
        Selection state dictionary or None
    """
    st.subheader("🔻 Project Funnel (WIP)")

    # Check if severity column exists for stacked view
    has_severity = "severity" in df.columns

    if has_severity:
        # Fill NaN severity with "Unset" for display
        # Convert to string first to handle Categorical dtype
        df_chart = df.copy()
        
        # Normalize severity: handle NaNs, convert to string, strip whitespace, and title case
        # This fixes issues where "Critical" and "critical " might be treated as different
        df_chart["severity"] = (
            df_chart["severity"]
            .astype(str)
            .replace("nan", "Unset")
            .replace("<NA>", "Unset")
            .replace("None", "Unset")
            .str.strip()
            .str.title()
        )
        # Ensure "Unset" remains "Unset" (title() handles it, but just to be sure if lowercased)
        
        # Consolidate stage_order: use the minimum order for each stage to prevent splitting
        # This handles cases where different rules assign different orders to the same stage name
        stage_order_map = df_chart.groupby("stage")["stage_order"].min()
        df_chart["stage_order"] = df_chart["stage"].map(stage_order_map)

        # Aggregation with severity breakdown
        stage_stats = df_chart.groupby(["stage", "stage_order", "severity"]).size().reset_index(name="count")

        # Sort by defined order
        stage_stats = stage_stats.sort_values("stage_order")

        if stage_stats.empty:
            st.info("No stage data.")
            return

        # Define priority color palette (semantic)
        priority_colors = {
            "Critical": COLORS.get("critical", "#EF4444"),
            "High": COLORS.get("high", "#F97316"),
            "Medium": COLORS.get("medium", "#EAB308"),
            "Low": COLORS.get("low", "#22C55E"),
            "Unset": COLORS.get("unset", "#94A3B8"),
        }

        fig = px.bar(
            stage_stats,
            x="count",
            y="stage",
            color="severity",
            orientation="h",
            text="count",
            title="",
            color_discrete_map=priority_colors,
            category_orders={"severity": ["Critical", "High", "Medium", "Low", "Unset"]},
            custom_data=["severity"], # Pass severity for filtering
        )

        fig.update_traces(textposition="inside")
    else:
        # Fallback: simple aggregation without severity
        stage_stats = df.groupby(["stage", "stage_order"]).size().reset_index(name="count")
        stage_stats = stage_stats.sort_values("stage_order")

        if stage_stats.empty:
            st.info("No stage data.")
            return None

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
        yaxis=dict(autorange="reversed"),  # Top to bottom flow
        xaxis=dict(showgrid=True, gridcolor="rgba(100,116,139,0.2)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None),
        barmode="stack",
    )

    return st.plotly_chart(
        fig, 
        width="stretch",
        on_select="rerun",
        selection_mode=["points"] 
    )




def _render_aging_chart(df: pd.DataFrame) -> dict | None:
    """Render boxplot of days in stage.
    
    Returns:
        Selection state dictionary or None
    """
    st.subheader("⏳ Stage Stickiness (Aging)")

    # Filter out completed/closed items to focus on active work aging
    # "Stickiness" implies items currently stuck in the flow.
    df = df[
        (df["stage_type"] != "completed") & 
        (df["state"] != "closed")
    ].copy()
    
    # Sort stages by order for x-axis
    df_sorted = df.sort_values("stage_order")

    if df_sorted.empty:
        st.info("No data.")
        return None

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

    return st.plotly_chart(
        fig, 
        width="stretch",
        on_select="rerun",
        selection_mode=["points"]
    )


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

    # 3. Sort by Hierarchy (Parent -> Child) or Staleness
    # User requested hierarchical view.
    if "parent_id" in display_df.columns:
        # parent_id contains IID, so we must map to 'iid' column, not 'id'
        display_df = sort_hierarchy(display_df, parent_col="parent_id", id_col="iid", title_col="title")
    else:
        display_df = display_df.sort_values("days_in_stage", ascending=False)

    # 4. Select Columns
    cols_to_show = [
        "web_url", "title", "stage", "days_in_stage", "severity", "context", "milestone", "assignee"
    ]
    # Filter columns that exist
    cols = [c for c in cols_to_show if c in display_df.columns]

    # 5. Configure Columns and Render
    display_df = display_df[cols]

    column_config = {
        "web_url": st.column_config.LinkColumn(
            "IID",
            display_text=r"/(?:issues|work_items)/(\d+)$",
            width="small",
            help="Click to open in GitLab"
        ),
        "assignee": st.column_config.TextColumn("Assignee", width="small"),
        "stage": st.column_config.TextColumn("Stage", width="small"),
        "title": st.column_config.TextColumn("Title", width="large"),
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
        label_colors = load_labels()
        
        def highlight_context(val):
            if not isinstance(val, str):
                return None
            color = label_colors.get(val)
            if color:
                return f'background-color: {color}; color: #ffffff' 
            return None

        styler = display_df.style.map(highlight_context, subset=["context"])

    column_order = ["web_url", "title", "stage", "days_in_stage", "severity", "milestone", "assignee"]
    if "context" in display_df.columns:
        column_order.insert(5, "context")

    st.dataframe(
        styler if styler is not None else display_df,
        column_config=column_config,
        column_order=column_order,
        use_container_width=True,
        hide_index=True,
    )
