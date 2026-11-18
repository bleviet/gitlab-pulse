"""Cache for Plotly figures built by the chart widgets.

Building a figure costs 10-25 ms in Plotly's validation, and most figures are
identical from one run to the next (a chart click changes the highlight of a
few). A widget therefore splits into data preparation, which runs every time,
and a module-level builder decorated with ``cache_figure`` that turns plain
arguments into the ``go.Figure``.

Rules for a builder:

- The cached figure is shared between runs and sessions, so it must never be
  mutated after it is returned.
- Every input of the figure must be an argument of the builder. Streamlit does
  not hash parameters whose name starts with an underscore, so builder
  parameters must not start with one.
- Anything the theme helpers read that is not an argument goes in through a
  ``theme_key`` argument (see ``theme_key``), so a theme switch gives a
  different cache entry.
- UI calls (``st.info``, ``st.plotly_chart``) do not belong in a builder.
"""

import streamlit as st

from app.dashboard.theme import (
    get_active_theme_mode,
    get_palette,
    get_priority_colors,
)

cache_figure = st.cache_resource(max_entries=256, show_spinner=False)


def theme_key() -> tuple[object, ...]:
    """Return what the theme helpers read that changes a figure's look.

    Builders take it as an argument named ``theme_key``, so a light/dark
    switch or changed rule colours give a different cache entry.

    Returns:
        A hashable tuple of the active mode, the palette and the priority
        colours.
    """
    return (
        get_active_theme_mode(),
        tuple(sorted(get_palette().items())),
        tuple(get_priority_colors().items()),
    )
