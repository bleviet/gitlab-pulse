"""Release Metrics KPI Widget."""

from typing import Any

import pandas as pd
import streamlit as st

from app.dashboard.components import style_metric_cards


def release_metrics(
    df: pd.DataFrame,
    milestone_name: str,
    progress: float,
    days_remaining: int,
    config: dict[str, Any] | None = None
) -> None:
    """Render Release page KPI cards (Milestone, Progress, Days Remaining, Total Issues).

    Args:
        df: DataFrame with issues for the milestone
        milestone_name: Name of the selected milestone
        progress: Completion percentage (0-100)
        days_remaining: Days until milestone due date
        config: Optional configuration (unused currently)
    """
    style_metric_cards()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Milestone", milestone_name, help="Selected release scope")

    with col2:
        st.metric("Progress", f"{progress:.0f}%", help="Completion rate")

    with col3:
        delta_text = "overdue" if days_remaining < 0 else "remaining"
        st.metric("Days Remaining", abs(days_remaining), delta=delta_text)

    with col4:
        st.metric("Total Issues", len(df), help="Issues in this milestone")
