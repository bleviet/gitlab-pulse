"""Stage Distribution Chart Widget.

Full-featured version matching overview.py implementation.
"""

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.dashboard.theme import FONT_FAMILY
from app.dashboard.theme import PALETTE as COLORS
from app.dashboard.theme import (get_plotly_font_color, plotly_bar_trace_style,
                                 plotly_layout)


def _contrast_text_color(color_value: str) -> str:
    """Return readable text color against a given background color."""
    value = (color_value or "").strip().lower()

    red: int
    green: int
    blue: int

    if value.startswith("#"):
        hex_value = value.lstrip("#")
        if len(hex_value) == 3:
            hex_value = "".join(ch * 2 for ch in hex_value)
        if len(hex_value) != 6:
            return "#F9FAFB"
        red = int(hex_value[0:2], 16)
        green = int(hex_value[2:4], 16)
        blue = int(hex_value[4:6], 16)
    elif value.startswith("rgb"):
        parts = (
            value.replace("rgba", "")
            .replace("rgb", "")
            .replace("(", "")
            .replace(")", "")
            .split(",")
        )
        if len(parts) < 3:
            return "#F9FAFB"
        red = int(float(parts[0].strip()))
        green = int(float(parts[1].strip()))
        blue = int(float(parts[2].strip()))
    else:
        return "#F9FAFB"

    luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255.0
    return "#111827" if luminance > 0.6 else "#F9FAFB"


def stage_distribution(
    df: pd.DataFrame, config: dict[str, Any] | None = None
) -> dict | None:
    """Render horizontal bar chart of issues per stage (Work by Stage).

    Features:
    - Severity stacked bars with priority colors
    - Total count labels at bar ends
    - Stage descriptions in hover tooltips
    - Visible stages filter
    - Stage ordering by workflow

    Args:
        df: DataFrame of issues
        config: Optional configuration with keys:
            - stage_descriptions: dict mapping stage names to descriptions
            - height: chart height in pixels
            - key: unique widget key

    Returns:
        Selection state dictionary or None
    """
    config = config or {}
    height = config.get("height", 400)
    widget_key = config.get("key", "stage_distribution")
    stage_descriptions = config.get("stage_descriptions", {})
    chart_text_color = get_plotly_font_color()

    # Use configured colors if available, else fallback to default
    palette = config.get(
        "colors", COLORS
    ).copy()  # Use copy to avoid mutating global default

    if df.empty or "stage" not in df.columns:
        st.info("No stage data available")
        return None

    total_issues = len(df)
    help_text = (
        "**Interaction Guide:**\n"
        "- **Hover** to view stage details.\n"
        "- **Click** a bar segment to filter tables below.\n"
        "- **Shift+Click** to select multiple segments.\n"
        "- **Double-Click** to reset selection."
    )
    st.subheader(f"Issues Total: {total_issues}", help=help_text)

    # Check if severity column exists for stacked view
    has_severity = "severity" in df.columns

    # Get all stages sorted by order
    if "stage_order" in df.columns:
        stage_orders = df.groupby("stage")["stage_order"].min().sort_values()
        all_stages = stage_orders.index.tolist()
    else:
        stage_order = ["Backlog", "To Do", "In Progress", "Review", "Done", "Closed"]
        all_stages = df["stage"].unique().tolist()
        all_stages = sorted(
            all_stages,
            key=lambda x: (
                stage_order.index(x) if x in stage_order else len(stage_order)
            ),
        )

    # Detect when available options change (e.g., milestone filter changed)
    # and reset the filter to show all stages
    options_hash = hash(tuple(all_stages))
    options_hash_key = f"{widget_key}_options_hash"
    filter_key = f"{widget_key}_stages_filter"

    # Check if options changed since last render
    if st.session_state.get(options_hash_key) != options_hash:
        # Options changed - reset filter by removing cached widget state
        if filter_key in st.session_state:
            del st.session_state[filter_key]
        st.session_state[options_hash_key] = options_hash

    # Visible stages filter
    with st.expander("🔍 Filters", expanded=False):
        selected_stages = st.multiselect(
            "Visible Stages",
            options=all_stages,
            default=all_stages,
            help="Deselect stages (like 'Done') to rescale the chart.",
            key=filter_key,
        )

    if not selected_stages:
        st.warning("Please select at least one stage.")
        return None

    # Filter data to selected stages
    df = df[df["stage"].isin(selected_stages)].copy()

    # Calculate totals per stage for the labels
    stage_totals = (
        df.groupby("stage", observed=True).size().reset_index(name="total_count")
    )

    if has_severity:
        # Normalize severity for display
        df_chart = df.copy()
        df_chart["severity"] = (
            df_chart["severity"]
            .astype(str)
            .replace("nan", "Unset")
            .replace("<NA>", "Unset")
            .replace("None", "Unset")
            .str.strip()
            .str.title()
        )

        # Get stage ordering
        if "stage_order" in df_chart.columns:
            stage_order_map = df_chart.groupby("stage")["stage_order"].min()
            df_chart["stage_order"] = df_chart["stage"].map(stage_order_map)
            stage_order_df = (
                df_chart[["stage", "stage_order"]]
                .drop_duplicates()
                .sort_values("stage_order")
            )
            sorted_stages = stage_order_df["stage"].tolist()
        else:
            sorted_stages = selected_stages

        # Aggregation with severity breakdown
        if "stage_order" in df_chart.columns:
            stage_stats = (
                df_chart.groupby(["stage", "stage_order", "severity"])
                .size()
                .reset_index(name="count")
            )
        else:
            stage_stats = (
                df_chart.groupby(["stage", "severity"]).size().reset_index(name="count")
            )

        # Add description
        if stage_descriptions:
            stage_stats["description"] = (
                stage_stats["stage"].map(stage_descriptions).fillna("")
            )
        else:
            stage_stats["description"] = ""

        # Calculate severity counts for legend
        severity_counts = df_chart["severity"].value_counts()
        severity_label_map = {
            sev: f"{sev} ({count})" for sev, count in severity_counts.items()
        }
        stage_stats["severity_label"] = stage_stats["severity"].map(severity_label_map)

        if "stage_order" in stage_stats.columns:
            stage_stats = stage_stats.sort_values("stage_order")

        if stage_stats.empty:
            st.info("No stage data.")
            return None

        # Priority color palette
        priority_colors = {
            "Critical": palette["critical"],
            "High": palette["high"],
            "Medium": palette["medium"],
            "Low": palette["low"],
            "Unset": palette["unset"],
        }

        # Build color map for formatted labels
        final_color_map = {}
        ordered_severity_labels = []
        base_severity_order = ["Critical", "High", "Medium", "Low", "Unset"]

        for sev in base_severity_order:
            if sev in severity_label_map:
                label = severity_label_map[sev]
                ordered_severity_labels.append(label)
                final_color_map[label] = priority_colors.get(
                    sev, priority_colors["Unset"]
                )

        for sev, label in severity_label_map.items():
            if label not in final_color_map:
                ordered_severity_labels.append(label)
                final_color_map[label] = priority_colors["Unset"]

        fig = px.bar(
            stage_stats,
            x="count",
            y="stage",
            color="severity_label",
            orientation="h",
            text="count",
            title="",
            color_discrete_map=final_color_map,
            category_orders={
                "severity_label": ordered_severity_labels,
                "stage": sorted_stages,
            },
            custom_data=["severity", "description"],
        )

        trace_style = plotly_bar_trace_style()
        trace_style["textposition"] = "auto"
        fig.update_traces(
            **trace_style,
            hovertemplate="<b>%{y}</b><br>%{customdata[1]}<br>Severity: %{customdata[0]}<br>Count: %{x}<extra></extra>",
        )

        for trace in fig.data:
            marker_color = None
            if (
                hasattr(trace, "marker")
                and getattr(trace.marker, "color", None) is not None
            ):
                marker_color = str(trace.marker.color)

            trace.update(
                textfont={
                    "color": _contrast_text_color(marker_color or ""),
                    "family": FONT_FAMILY,
                },
                insidetextanchor="middle",
            )

        fig.update_layout(legend_title_text="Priority")
    else:
        # Simple aggregation without severity
        if "stage_order" in df.columns:
            stage_stats = (
                df.groupby(["stage", "stage_order"]).size().reset_index(name="count")
            )
            stage_stats = stage_stats.sort_values("stage_order")
            stage_order_df = (
                df[["stage", "stage_order"]]
                .drop_duplicates()
                .sort_values("stage_order")
            )
            sorted_stages = stage_order_df["stage"].tolist()
        else:
            stage_stats = df.groupby("stage").size().reset_index(name="count")
            sorted_stages = selected_stages

        if stage_stats.empty:
            st.info("No stage data.")
            return None

        fig = px.bar(
            stage_stats,
            x="count",
            y="stage",
            orientation="h",
            text="count",
            title="",
            category_orders={"stage": sorted_stages},
        )
        fig.update_traces(
            marker_color=palette["primary"],
            marker_line_width=0,
            textposition="auto",
            textfont={"color": chart_text_color, "family": FONT_FAMILY},
        )

    # Add Total Labels at bar ends
    stage_totals = stage_totals[stage_totals["stage"].isin(sorted_stages)]

    fig.add_trace(
        go.Scatter(
            x=stage_totals["total_count"],
            y=stage_totals["stage"],
            mode="text",
            text=stage_totals["total_count"].apply(lambda x: f"({x})"),
            textposition="middle right",
            hoverinfo="skip",
            showlegend=False,
            textfont=dict(color=chart_text_color, family=FONT_FAMILY),
        )
    )

    # Calculate max range to fit labels
    max_count = stage_totals["total_count"].max() if not stage_totals.empty else 0

    fig.update_layout(
        **plotly_layout(
            height=height,
            show_xgrid=False,
            show_ygrid=False,
        ),
        barmode="stack",
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )
    fig.update_xaxes(showgrid=False, range=[0, max_count * 1.15])

    selection = st.plotly_chart(
        fig,
        width="stretch",
        on_select="rerun",
        selection_mode=["points"],
        key=widget_key,
    )

    return selection
