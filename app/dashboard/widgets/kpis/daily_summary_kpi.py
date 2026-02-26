"""Daily Summary KPI Widget."""

from typing import Any

import pandas as pd
import streamlit as st

from app.dashboard.components import style_metric_cards


def daily_summary_kpi(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None,
) -> None:
    """Render KPI cards for daily issue activity.

    Displays New, Closed, and Net Change counts
    scoped to issues since yesterday midnight (00:00 UTC).

    Args:
        df: DataFrame with valid issues
        config: Optional configuration with keys:
            - cutoff: pd.Timestamp for the cutoff (default: yesterday 00:00 UTC)
    """
    config = config or {}
    cutoff = config.get(
        "cutoff",
        pd.Timestamp.now(tz="UTC").normalize() - pd.Timedelta(days=1),
    )

    style_metric_cards()

    new_count = 0
    closed_count = 0

    if not df.empty:
        if "created_at" in df.columns:
            new_count = int((df["created_at"] >= cutoff).sum())
        if "closed_at" in df.columns:
            closed_count = int((df["closed_at"] >= cutoff).sum())

    net_change = new_count - closed_count

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="🆕 New Issues", value=new_count)
    with col2:
        st.metric(label="✅ Closed Issues", value=closed_count)
    with col3:
        st.metric(
            label="📊 Net Change",
            value=net_change,
            delta=f"{net_change:+d}",
            delta_color="inverse",
        )
