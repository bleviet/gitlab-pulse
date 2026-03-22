"""Quality Score KPI Widget."""

from typing import Any

import pandas as pd
import streamlit as st

from app.dashboard.widgets.quality_metrics import compute_quality_summary


def quality_score(
    valid_df: pd.DataFrame,
    quality_df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> None:
    """Render quality score metric.

    Args:
        valid_df: DataFrame with valid issues
        quality_df: DataFrame with quality (failed) issues
        config: Optional configuration (unused currently)
    """
    score = compute_quality_summary(valid_df, quality_df)["score"]

    st.metric("Quality Score", f"{score}%", help="Percentage of issues without validation hints")
