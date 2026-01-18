"""Aging Page (Operational View) for Layer 3 Dashboard.

Boxplots for age distribution and stale issue alerts.
"""

import pandas as pd
import plotly.express as px
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


def render_aging(df: pd.DataFrame) -> None:
    """Render the Aging (Operational) page.

    Args:
        df: Filtered DataFrame with valid issues
    """
    st.header("⏱️ Aging Analysis")
    st.caption("Operational view for identifying bottlenecks")

    if df.empty:
        st.warning("No data available. Run the collector and processor first.")
        return

    # Alert Banner for stale issues
    _render_stale_alert(df)

    # Boxplot by Issue Type
    st.subheader("📊 Age Distribution by Type")
    _render_age_boxplot(df, "issue_type")

    st.divider()

    # Boxplot by Severity
    if "severity" in df.columns and not df["severity"].isna().all():
        st.subheader("📊 Age Distribution by Severity")
        _render_age_boxplot(df, "severity")

    st.divider()

    # Stale Issues Table
    _render_stale_table(df)


def _render_stale_alert(df: pd.DataFrame) -> None:
    """Render alert banner if too many stale issues."""
    if "is_stale" not in df.columns:
        return

    stale_count = len(df[df["is_stale"] == True])
    open_count = len(df[df["state"] == "opened"])

    if open_count == 0:
        return

    stale_ratio = stale_count / open_count

    if stale_ratio > 0.2:  # More than 20% stale
        st.warning(
            f"⚠️ **High volume of stale issues detected!** "
            f"{stale_count} issues ({stale_ratio:.0%} of open) have not been updated recently.",
            icon="⚠️",
        )
    elif stale_count > 0:
        st.info(
            f"ℹ️ {stale_count} stale issue(s) need attention.",
            icon="ℹ️",
        )


def _render_age_boxplot(df: pd.DataFrame, group_col: str) -> None:
    """Render boxplot of age_days grouped by a column."""
    if group_col not in df.columns or df[group_col].isna().all():
        st.info(f"No {group_col} data available for boxplot")
        return

    if "age_days" not in df.columns:
        st.info("No age data available")
        return

    # Only open issues for aging analysis
    open_df = df[df["state"] == "opened"].copy()

    if open_df.empty:
        st.info("No open issues to analyze")
        return

    # Color mapping
    color_map = {
        "Bug": COLORS["bug"],
        "Feature": COLORS["feature"],
        "Task": COLORS["task"],
        "Epic": "#8B5CF6",
        "Critical": COLORS["bug"],
        "High": COLORS["stale"],
        "Medium": COLORS["primary"],
        "Low": COLORS["neutral"],
    }

    fig = px.box(
        open_df,
        x=group_col,
        y="age_days",
        color=group_col,
        color_discrete_map=color_map,
        hover_data=["title", "assignee", "age_days"],
        points="outliers",
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        xaxis=dict(showgrid=False, title=""),
        yaxis=dict(
            gridcolor="rgba(100,116,139,0.2)",
            title="Age (Days)",
        ),
    )

    # Custom hover template
    fig.update_traces(
        hovertemplate="<b>%{customdata[0]}</b><br>"
                      "Assignee: %{customdata[1]}<br>"
                      "Age: %{y} days<extra></extra>",
    )

    st.plotly_chart(fig, width="stretch")


def _render_stale_table(df: pd.DataFrame) -> None:
    """Render table of stale issues."""
    st.subheader("📋 Stale Issues List")

    if "is_stale" not in df.columns:
        st.info("No staleness data available")
        return

    stale_df = df[df["is_stale"] == True].copy()

    if stale_df.empty:
        st.success("✅ No stale issues! All issues are actively maintained.")
        return

    # Select display columns
    display_cols = ["iid", "title", "issue_type", "assignee", "age_days", "updated_at"]
    available_cols = [c for c in display_cols if c in stale_df.columns]

    display_df = stale_df[available_cols].sort_values("age_days", ascending=False)

    # Format for display
    if "updated_at" in display_df.columns:
        display_df["updated_at"] = display_df["updated_at"].dt.strftime("%Y-%m-%d")

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config={
            "iid": st.column_config.NumberColumn("IID", width="small"),
            "title": st.column_config.TextColumn("Title", width="large"),
            "issue_type": st.column_config.TextColumn("Type", width="small"),
            "assignee": st.column_config.TextColumn("Assignee", width="medium"),
            "age_days": st.column_config.NumberColumn("Age (Days)", width="small"),
            "updated_at": st.column_config.TextColumn("Last Update", width="medium"),
        },
    )
