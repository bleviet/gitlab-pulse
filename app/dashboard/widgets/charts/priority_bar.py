"""Priority Bar Chart Widget."""

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from app.dashboard.theme import get_palette, get_plotly_font_color, plotly_layout


def priority_bar(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render bar chart of open issues by priority.

    Args:
        df: DataFrame of issues
        config: Optional configuration
    """
    config = config or {}
    height = config.get("height", 250)
    widget_key = config.get("key", "priority_bar")

    if df.empty or "severity" not in df.columns:
        st.info("No priority data.")
        return None

    work_df = df[df["state"] == "opened"].copy() if "state" in df.columns else df.copy()

    if work_df.empty:
        st.info("No open issues.")
        return None

    # Normalize severity
    work_df["severity"] = work_df["severity"].astype(str).str.strip().str.title()
    work_df.loc[work_df["severity"].isin(["None", "Nan", "<Na>", ""]), "severity"] = "Low"
    
    priority_counts = work_df["severity"].value_counts().reset_index()
    priority_counts.columns = ["Priority", "Count"]

    if priority_counts["Count"].sum() == 0:
        return None

    palette = get_palette()
    
    colors_map = {
        "Critical": palette.get("critical", "#e74c3c"),
        "High": palette.get("high", "#e67e22"),
        "Medium": palette.get("medium", "#f1c40f"),
        "Low": palette.get("low", "#2ecc71"),
    }
    
    order = ["Critical", "High", "Medium", "Low"]
    priority_counts["Sort"] = priority_counts["Priority"].map(lambda x: order.index(x) if x in order else 99)
    priority_counts = priority_counts.sort_values("Sort")

    fig = px.bar(
        priority_counts,
        x="Priority",
        y="Count",
        color="Priority",
        color_discrete_map=colors_map,
        orientation="v",
    )
    
    fig.update_traces(
        marker_line_width=0,
        text=[f"<b>{c}</b>" for c in priority_counts["Count"]],
        textposition="outside",
        textfont=dict(color=get_plotly_font_color(), size=12) 
    )

    fig.update_layout(
        **plotly_layout(
            height=height,
            show_xgrid=False,
            show_ygrid=False,
            margin=dict(l=0, r=0, t=20, b=0),
            legend_pos="none",
        ),
    )
    
    fig.update_xaxes(showgrid=False, title="", showticklabels=True, tickfont=dict(size=10))
    fig.update_yaxes(showgrid=False, title="", showticklabels=False, range=[0, priority_counts["Count"].max() * 1.3])

    selection = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        selection_mode=["points"],
        key=widget_key,
    )

    return selection
