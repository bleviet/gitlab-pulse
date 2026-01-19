"""Overview Page (Strategic View) for Layer 3 Dashboard.

KPI cards, burn-up chart, and distribution visualizations.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Semantic color palette
COLORS = {
    "primary": "#4F46E5",
    "bug": "#EF4444",
    "feature": "#3B82F6",
    "task": "#10B981",
    "stale": "#F59E0B",
    "neutral": "#64748B",
    "epic": "#8B5CF6",
}


def render_overview(df: pd.DataFrame, colors: dict[str, str] | None = None) -> None:
    """Render the Overview (Strategic) page.

    Args:
        df: Filtered DataFrame with valid issues
        colors: Optional dictionary of semantic colors to override defaults
    """
    if colors:
        COLORS.update(colors)

    st.header("📊 Overview")
    st.caption("Strategic view of project velocity and distribution")

    if df.empty:
        st.warning("No data available. Run the collector and processor first.")
        return

    # Top Row: KPI Cards
    _render_kpi_cards(df)

    # Middle Row: Burn-up Chart (Collapsible)
    with st.expander("📈 Cumulative Flow by Type", expanded=True):
        _render_burnup_chart(df)

    # Bottom Row: Distribution Charts (Collapsible)
    with st.expander("📊 Distribution Charts", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            _render_work_distribution(df)
        with col2:
            _render_status_donut(df)


def _render_kpi_cards(df: pd.DataFrame) -> None:
    """Render KPI metric cards."""
    col1, col2, col3, col4 = st.columns(4)

    # Total Open Issues
    open_count = len(df[df["state"] == "opened"])
    with col1:
        st.metric(
            label="Open Issues",
            value=open_count,
            delta=None,
        )

    # Velocity (Closed per Week)
    closed_df = df[df["state"] == "closed"].copy()
    if not closed_df.empty and "closed_at" in closed_df.columns:
        closed_df["week"] = closed_df["closed_at"].dt.isocalendar().week
        weekly_closed = closed_df.groupby("week").size()
        velocity = round(weekly_closed.mean(), 1) if len(weekly_closed) > 0 else 0
    else:
        velocity = 0

    with col2:
        st.metric(
            label="Velocity (Closed/Week)",
            value=velocity,
        )

    # Bug Ratio
    bug_count = len(df[df["issue_type"] == "Bug"])
    total_count = len(df)
    bug_ratio = round((bug_count / total_count) * 100, 1) if total_count > 0 else 0

    with col3:
        st.metric(
            label="Bug Ratio",
            value=f"{bug_ratio}%",
        )

    # Stale Issues
    stale_count = len(df[df.get("is_stale", False) == True])
    with col4:
        st.metric(
            label="Stale Issues",
            value=stale_count,
            delta_color="inverse" if stale_count > 0 else "off",
        )


def _render_burnup_chart(df: pd.DataFrame) -> None:
    """Render Faceted Cumulative Flow Diagram (Small Multiples).

    3 stacked panels: Features (top), Bugs (middle), Tasks (bottom).
    All share the same X-axis (time) for vertical correlation.
    """
    st.subheader("📈 Cumulative Flow by Type")

    if df.empty:
        st.info("No data for cumulative flow chart")
        return

    # Prepare weekly data (remove timezone before period conversion)
    df_copy = df.copy()
    df_copy["created_week"] = df_copy["created_at"].dt.tz_localize(None).dt.to_period("W").dt.start_time

    # Panel configuration per TSD spec
    panels = [
        {"type": "Feature", "title": "Features (Value Flow)", "fill": "#166534", "area": "#BBF7D0"},
        {"type": "Bug", "title": "Bugs (Failure Demand)", "fill": "#991B1B", "area": "#FCA5A5"},
        {"type": "Task", "title": "Tasks (Maintenance)", "fill": "#374151", "area": "#D1D5DB"},
    ]

    # Create subplots with shared X-axis
    from plotly.subplots import make_subplots

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=[p["title"] for p in panels],
    )

    # Get all weeks for consistent x-axis
    all_weeks = sorted(df_copy["created_week"].unique())

    for i, panel in enumerate(panels, start=1):
        type_df = df_copy[df_copy["issue_type"] == panel["type"]].copy()

        if type_df.empty:
            # Add empty traces for consistency
            fig.add_trace(go.Scatter(
                x=all_weeks, y=[0] * len(all_weeks),
                mode="lines", name=f'{panel["type"]} Created',
                line=dict(color=panel["fill"], width=2),
                showlegend=False,
            ), row=i, col=1)
            continue

        # Calculate cumulative created
        weekly_created = type_df.groupby("created_week").size().reindex(all_weeks, fill_value=0).cumsum()

        # Calculate cumulative closed
        closed_df = type_df[type_df["closed_at"].notna()].copy()
        if not closed_df.empty:
            closed_df["closed_week"] = closed_df["closed_at"].dt.tz_localize(None).dt.to_period("W").dt.start_time
            weekly_closed = closed_df.groupby("closed_week").size().reindex(all_weeks, fill_value=0).cumsum()
        else:
            weekly_closed = pd.Series([0] * len(all_weeks), index=all_weeks)

        # Total Created line (background - shows scope)
        fig.add_trace(go.Scatter(
            x=weekly_created.index,
            y=weekly_created.values,
            mode="lines",
            name=f'{panel["type"]} Created',
            line=dict(color=panel["fill"], width=2),
            fill="tozeroy",
            fillcolor=panel["area"],
            showlegend=False,
            hovertemplate="Created: %{y}<extra></extra>",
        ), row=i, col=1)

        # Total Closed filled area (foreground - shows completed work)
        fig.add_trace(go.Scatter(
            x=weekly_closed.index,
            y=weekly_closed.values,
            mode="lines",
            name=f'{panel["type"]} Closed',
            line=dict(color=panel["fill"], width=2),
            fill="tozeroy",
            fillcolor=panel["fill"],
            showlegend=False,
            hovertemplate="Closed: %{y}<extra></extra>",
        ), row=i, col=1)

    # Update layout per TSD spec
    fig.update_layout(
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hovermode="x unified",
    )

    # Per-panel y-axis settings (independent scaling)
    for i in range(1, 4):
        fig.update_yaxes(
            showgrid=True,
            gridcolor="rgba(100,116,139,0.2)",
            zeroline=False,
            row=i, col=1,
        )
        fig.update_xaxes(
            showgrid=False,
            showticklabels=(i == 3),  # Only show x-axis labels on bottom panel
            row=i, col=1,
        )

    st.plotly_chart(fig, width="stretch")


def _render_work_distribution(df: pd.DataFrame) -> None:
    """Render work distribution bar chart."""
    st.subheader("📦 Work Distribution")

    if "issue_type" not in df.columns or df["issue_type"].isna().all():
        st.info("No issue type data available")
        return

    type_counts = df["issue_type"].value_counts().reset_index()
    type_counts.columns = ["Type", "Count"]

    # Map colors
    color_map = {
        "Bug": COLORS["bug"],
        "Feature": COLORS["feature"],
        "Task": COLORS["task"],
        "Task": COLORS["task"],
        "Epic": COLORS["epic"],
    }

    fig = px.bar(
        type_counts,
        x="Count",
        y="Type",
        orientation="h",
        color="Type",
        color_discrete_map=color_map,
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(gridcolor="rgba(100,116,139,0.2)"),
        yaxis=dict(showgrid=False),
    )

    st.plotly_chart(fig, width="stretch")


def _render_status_donut(df: pd.DataFrame) -> None:
    """Render status split donut chart."""
    st.subheader("🎯 Status Split")

    status_counts = df["state"].value_counts().reset_index()
    status_counts.columns = ["State", "Count"]

    color_map = {
        "opened": COLORS["stale"],
        "closed": COLORS["task"],
    }

    fig = px.pie(
        status_counts,
        values="Count",
        names="State",
        hole=0.6,
        color="State",
        color_discrete_map=color_map,
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.1),
    )

    st.plotly_chart(fig, width="stretch")
