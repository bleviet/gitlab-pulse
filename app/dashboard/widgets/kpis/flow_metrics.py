"""Flow Metrics KPI Widget."""

from typing import Any

import pandas as pd
import streamlit as st

from app.dashboard.components import style_metric_cards


def flow_metrics(df: pd.DataFrame, config: dict[str, Any] | None = None) -> None:
    """Render Flow key metrics (Active WIP, Flow Efficiency, Bottleneck, Max Idle).

    Args:
        df: DataFrame of issues (should be unique/deduplicated)
        config: Optional configuration (unused currently)
    """
    style_metric_cards()

    col1, col2, col3, col4 = st.columns(4)

    # 1. Active WIP
    active_mask = df["stage_type"] == "active"
    active_count = len(df[active_mask])

    with col1:
        st.metric("Active Work In Progress", active_count, help="Issues in active stages")

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
        st.metric("Max Idle Days", f"{max_days} days", help="Longest time in current stage")
