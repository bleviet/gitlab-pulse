"""Priority Donut Chart Widget."""

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.theme import get_palette, get_plotly_font_color, plotly_layout


def priority_donut(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> dict | None:
    """Render donut chart of open issues by priority.

    Args:
        df: DataFrame of issues
        config: Optional configuration
    """
    config = config or {}
    height = config.get("height", 250)
    widget_key = config.get("key", "priority_donut")
    center_text = config.get("center_text", "OPEN<br>ISSUES")
    show_legend = config.get("show_legend", True)

    if df.empty or "severity" not in df.columns:
        st.info("No priority data available.")
        return None

    state_filter = config.get("state_filter", "opened")
    if "state" in df.columns:
        if state_filter == "all":
            work_df = df.copy()
        else:
            work_df = df[df["state"] == state_filter].copy()
    else:
        work_df = df.copy()

    if work_df.empty:
        st.info(f"No {state_filter if state_filter != 'all' else ''} issues.")
        return None

    # Normalize severity
    work_df["severity"] = work_df["severity"].astype(str).str.strip().str.title()
    work_df.loc[work_df["severity"].isin(["None", "Nan", "<Na>", ""]), "severity"] = "Low"
    
    priority_counts = work_df["severity"].value_counts().reset_index()
    priority_counts.columns = ["Priority", "Count"]

    total_issues = priority_counts["Count"].sum()
    if total_issues == 0:
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
    
    labels = priority_counts["Priority"].tolist()
    values = priority_counts["Count"].tolist()
    colors = [colors_map.get(lbl, palette.get("neutral", "#95a5a6")) for lbl in labels]

    text_color = get_plotly_font_color()

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors),
        textinfo="value",
        textposition="inside",
        textfont=dict(color="#ffffff", size=12),
        showlegend=show_legend,
        sort=False,
    )])

    fig.add_annotation(
        text=f"<b style='font-size:28px; color:{text_color};'>{total_issues}</b><br><span style='font-size:12px; color:{text_color};'>{center_text}</span>",
        x=0.5, y=0.5,
        font=dict(family="Inter, sans-serif"),
        showarrow=False,
        xanchor="center",
        yanchor="middle",
    )

    fig.update_layout(
        **plotly_layout(
            height=height,
            margin=dict(l=0, r=0 if not show_legend else 20, t=10, b=10),
            legend_pos="right" if show_legend else "none",
        ),
    )
    
    fig.update_layout(
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.0
        )
    )

    show_modebar = st.session_state.get("show_chart_controls", False)

    selection = st.plotly_chart(
        fig, 
        width="stretch", 
        on_select="rerun",
        selection_mode=["points"],
        key=widget_key,
        config={"displayModeBar": show_modebar}
    )

    return selection
