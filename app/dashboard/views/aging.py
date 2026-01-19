"""Aging Page (Operational View) for Layer 3 Dashboard.

Boxplots for age distribution and stale issue alerts.
"""

import pandas as pd
import plotly.express as px
import streamlit as st
from app.dashboard.utils import sort_hierarchy

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



def render_aging(df: pd.DataFrame, colors: dict[str, str] | None = None) -> None:
    """Render the Aging (Operational) page.

    Args:
        df: Filtered DataFrame with valid issues
        colors: Optional dictionary of semantic colors to override defaults
    """
    if colors:
        COLORS.update(colors)

    st.header("⏱️ Aging Analysis")
    st.caption("Operational view for identifying bottlenecks")

    if df.empty:
        st.warning("No data available. Run the collector and processor first.")
        return

    # Alert Banner for stale issues
    _render_stale_alert(df)

    # Boxplot by Issue Type (Collapsible)
    with st.expander("📊 Age Distribution by Type", expanded=True):
        _render_age_boxplot(df, "issue_type")

    # Boxplot by Severity (Collapsible)
    if "severity" in df.columns and not df["severity"].isna().all():
        with st.expander("📊 Age Distribution by Severity", expanded=True):
            _render_age_boxplot(df, "severity")

    # Stale Issues Table (Collapsible)
    with st.expander("⚠️ Stale Issues", expanded=True):
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
        "Task": COLORS["task"],
        "Epic": COLORS["epic"],
        "Critical": COLORS.get("critical", COLORS["bug"]),
        "High": COLORS.get("high", COLORS["stale"]),
        "Medium": COLORS.get("medium", COLORS["primary"]),
        "Low": COLORS.get("low", COLORS["neutral"]),
        "Unset": COLORS.get("unset", COLORS["neutral"]),
        "P1": COLORS.get("p1", COLORS["bug"]),
        "P2": COLORS.get("p2", COLORS["primary"]),
        "P3": COLORS.get("p3", COLORS["neutral"]),
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
    # Select display columns (Include web_url, exclude separate iid if we merge)
    display_cols = ["web_url", "title", "issue_type", "assignee", "age_days", "updated_at"]
    # Wait, we need 'web_url' to be the data for 'IID' column
    available_cols = [c for c in display_cols if c in stale_df.columns]

    display_df = stale_df[available_cols].copy()
    
    if "parent_id" in display_df.columns:
         display_df = sort_hierarchy(display_df, parent_col="parent_id", id_col="iid", title_col="title")
    else:
         display_df = display_df.sort_values("age_days", ascending=False)

    # Format for display
    if "updated_at" in display_df.columns:
        display_df["updated_at"] = display_df["updated_at"].dt.strftime("%Y-%m-%d")

    # Rename web_url to IID for the table
    display_df = display_df.rename(columns={"web_url": "IID", "title": "Title", "issue_type": "Type", "assignee": "Assignee", "age_days": "Age (Days)", "updated_at": "Last Update"})

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_order=["IID", "Title", "Type", "Assignee", "Age (Days)", "Last Update"],
        column_config={
            "IID": st.column_config.LinkColumn(
                "IID",
                display_text=r"/(?:issues|work_items)/(\d+)$",
                width="small",
            ),
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Assignee": st.column_config.TextColumn("Assignee", width="medium"),
            "Age (Days)": st.column_config.NumberColumn("Age (Days)", width="small"),
            "Last Update": st.column_config.TextColumn("Last Update", width="medium"),
        },
    )
