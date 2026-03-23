"""Stale Count KPI Widget."""

from typing import Any

import pandas as pd
import streamlit as st


def stale_count(df: pd.DataFrame, config: dict[str, Any] | None = None) -> None:
    """Render single stale issue count metric.

    Args:
        df: DataFrame with issues
        config: Optional configuration (unused currently)
    """
    if "is_stale" not in df.columns:
        count = 0
    else:
        count = len(df[df["is_stale"] == True])

    st.metric("Stale Issues", count, help="Issues without recent updates")
