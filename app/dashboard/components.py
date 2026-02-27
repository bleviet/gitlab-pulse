import streamlit as st


def style_metric_cards() -> None:
    """Apply metric card styling.

    Card CSS is now injected globally via ``app.dashboard.theme.get_global_css()``
    which is called once in ``main.py``.  This function is kept as a no-op for
    backward compatibility so existing KPI widgets don't break.

    See: docs/spec/TSD_Layer3_PresentationLayer.md (ADR 5.4 & 7.1)
    """
    # Styling is handled by the global CSS in theme.py — nothing to inject here.
    pass
