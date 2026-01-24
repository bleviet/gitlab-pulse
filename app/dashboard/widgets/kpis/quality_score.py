"""Quality Score KPI Widget."""

from typing import Any

import pandas as pd
import streamlit as st


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
    total_valid = len(valid_df)
    total_quality = len(quality_df)
    total = total_valid + total_quality

    if total == 0:
        score = 0
    else:
        score = round((total_valid / total) * 100, 1)

    st.metric("Quality Score", f"{score}%", help="Percentage of valid issues")
