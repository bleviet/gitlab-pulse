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

    Displays New, Closed, and Net Change counts scoped to a 24-hour window.

    Args:
        df: DataFrame with valid issues
        config: Optional configuration with keys:
            - cutoff: pd.Timestamp for the window start (default: yesterday 00:00 UTC)
            - cutoff_end: pd.Timestamp for the window end (default: unbounded)
    """
    config = config or {}
    cutoff = config.get(
        "cutoff",
        pd.Timestamp.now(tz="UTC").normalize() - pd.Timedelta(days=1),
    )
    cutoff_end: pd.Timestamp | None = config.get("cutoff_end", None)

    style_metric_cards()

    new_count = 0
    closed_count = 0

    if not df.empty:
        if "created_at" in df.columns:
            mask = df["created_at"] >= cutoff
            if cutoff_end is not None:
                mask &= df["created_at"] < cutoff_end
            new_count = int(mask.sum())
        if "closed_at" in df.columns:
            mask = df["closed_at"] >= cutoff
            if cutoff_end is not None:
                mask &= df["closed_at"] < cutoff_end
            closed_count = int(mask.sum())

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
