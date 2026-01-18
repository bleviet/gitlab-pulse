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
}


def render_overview(df: pd.DataFrame) -> None:
    """Render the Overview (Strategic) page.

    Args:
        df: Filtered DataFrame with valid issues
    """
    st.header("📊 Overview")
    st.caption("Strategic view of project velocity and distribution")

    if df.empty:
        st.warning("No data available. Run the collector and processor first.")
        return

    # Top Row: KPI Cards
    _render_kpi_cards(df)

    st.divider()

    # Middle Row: Burn-up Chart
    _render_burnup_chart(df)

    st.divider()

    # Bottom Row: Distribution Charts
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
    """Render cumulative burn-up line chart."""
    st.subheader("📈 Cumulative Flow")

    if df.empty:
        st.info("No data for burn-up chart")
        return

    # Group by week (remove timezone before period conversion to avoid warning)
    df_copy = df.copy()
    df_copy["created_week"] = df_copy["created_at"].dt.tz_localize(None).dt.to_period("W").dt.start_time

    # Calculate cumulative created
    weekly_created = df_copy.groupby("created_week").size().cumsum().reset_index()
    weekly_created.columns = ["week", "Created"]

    # Calculate cumulative closed
    closed_df = df_copy[df_copy["closed_at"].notna()].copy()
    if not closed_df.empty:
        closed_df["closed_week"] = closed_df["closed_at"].dt.tz_localize(None).dt.to_period("W").dt.start_time
        weekly_closed = closed_df.groupby("closed_week").size().cumsum().reset_index()
        weekly_closed.columns = ["week", "Closed"]

        # Merge
        chart_df = weekly_created.merge(weekly_closed, on="week", how="left").ffill().fillna(0)
    else:
        chart_df = weekly_created
        chart_df["Closed"] = 0

    # Create Plotly chart
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=chart_df["week"],
        y=chart_df["Created"],
        mode="lines",
        name="Created",
        line=dict(color=COLORS["primary"], width=2),
        fill="tozeroy",
        fillcolor="rgba(79, 70, 229, 0.1)",
    ))

    fig.add_trace(go.Scatter(
        x=chart_df["week"],
        y=chart_df["Closed"],
        mode="lines",
        name="Closed",
        line=dict(color=COLORS["task"], width=2),
        fill="tozeroy",
        fillcolor="rgba(16, 185, 129, 0.1)",
    ))

    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(100,116,139,0.2)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
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
        "Epic": "#8B5CF6",
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
