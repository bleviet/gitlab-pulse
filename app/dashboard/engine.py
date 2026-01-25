"""Dashboard Grid Engine for Layer 3.

Renders widgets in a drag-and-drop grid using streamlit-elements.
Supports View Mode (locked) and Edit Mode (draggable/resizable).
"""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from streamlit_elements import elements, dashboard, mui, sync

from app.dashboard.registry import WidgetRegistry

# Layout storage directory
LAYOUTS_DIR = Path("data/config/layouts")


def load_layout(name: str = "default") -> dict:
    """Load a layout from JSON file.

    Args:
        name: Layout name (without .json extension)

    Returns:
        Layout dictionary with name, description, and layout items
    """
    layout_path = LAYOUTS_DIR / f"{name}.json"

    if not layout_path.exists():
        # Return empty layout if not found
        return {
            "name": name,
            "description": "",
            "layout": []
        }

    with open(layout_path, "r") as f:
        return json.load(f)


def save_layout(name: str, layout_data: dict) -> None:
    """Save a layout to JSON file.

    Args:
        name: Layout name (without .json extension)
        layout_data: Layout dictionary to save
    """
    LAYOUTS_DIR.mkdir(parents=True, exist_ok=True)
    layout_path = LAYOUTS_DIR / f"{name}.json"

    with open(layout_path, "w") as f:
        json.dump(layout_data, f, indent=2)


def delete_layout(name: str) -> bool:
    """Delete a layout file.

    Args:
        name: Layout name (without .json extension)

    Returns:
        True if deleted, False if not found or is default
    """
    if name == "default":
        return False  # Prevent deleting default layout

    layout_path = LAYOUTS_DIR / f"{name}.json"
    if layout_path.exists():
        layout_path.unlink()
        return True
    return False


def list_layouts() -> list[str]:
    """List all available layouts.

    Returns:
        List of layout names (without .json extension)
    """
    if not LAYOUTS_DIR.exists():
        return ["default"]

    layouts = [f.stem for f in LAYOUTS_DIR.glob("*.json")]
    return layouts if layouts else ["default"]


def create_layout(name: str, description: str = "") -> dict:
    """Create a new empty layout.

    Args:
        name: Layout name
        description: Optional description

    Returns:
        New layout dictionary
    """
    layout_data = {
        "name": name,
        "description": description,
        "layout": []
    }
    save_layout(name, layout_data)
    return layout_data


def render_grid(
    df: pd.DataFrame,
    layout_data: dict,
    edit_mode: bool = False,
    key: str = "dashboard_grid",
    quality_df: pd.DataFrame = None,
    widget_data_overrides: dict[str, pd.DataFrame] | None = None,
    key_suffix: str = "",
    global_config: dict[str, Any] | None = None
) -> dict | None:
    """Render widgets using Hybrid Strategy: Edit Mode (Blueprint) vs View Mode (Native).

    Args:
        df: DataFrame with issue data
        layout_data: Layout dictionary
        edit_mode: If True, uses streamlit-elements for drag-and-drop
        key: Unique key

    Returns:
        Updated layout if changed in edit mode
    """
    layout_items = layout_data.get("layout", [])

    if not layout_items and not edit_mode:
        st.info("No widgets in this layout. Switch to Edit Mode to add widgets.")
        return None

    # --- EDIT MODE: Draggable Grid with Embedded Delete (Callback) ---
    if edit_mode:
        if not layout_items:
            st.warning("No widgets yet. Use the Widget Toolbox in the sidebar to add widgets.")
            return None

        st.caption(f"📐 Editing {len(layout_items)} widget(s) • Drag to reposition • Resize from corners • Click ✕ to delete")

        # Inject CSS for grid visualization
        st.markdown("""
        <style>
        /* Grid background pattern for 12-column visualization */
        .stElementsFrame iframe {
            background-image:
                linear-gradient(to right, rgba(79, 70, 229, 0.1) 1px, transparent 1px);
            background-size: calc(100% / 12) 100%;
        }

        /* Resize handles styling */
        .react-resizable-handle {
            background-color: #4F46E5 !important;
            border-radius: 3px !important;
            opacity: 0.8 !important;
        }
        .react-resizable-handle:hover {
            opacity: 1 !important;
            background-color: #3730A3 !important;
        }
        </style>
        """, unsafe_allow_html=True)

        # Build dashboard layout items with resize handles on all corners
        grid_layout = [
            dashboard.Item(
                str(item["i"]),
                int(item["x"]),
                int(item["y"]),
                int(item["w"]),
                int(item["h"]),
                isResizable=True,
                isDraggable=True,
            )
            for item in layout_items
        ]

        # Session state key for tracking layout changes
        layout_state_key = f"{key}_layout_state"
        delete_state_key_prefix = f"{key}_delete_widget"
        last_delete_key = f"{key}_last_delete_widget"
        elements_frame_key = f"streamlit_elements.core.frame.elements_frame.{key}"

        def _find_delete_key(payload: object) -> str | None:
            if isinstance(payload, dict):
                for key_name, value in payload.items():
                    if isinstance(key_name, str) and key_name.startswith(f"{delete_state_key_prefix}_"):
                        return key_name
                    nested = _find_delete_key(value)
                    if nested:
                        return nested
            elif isinstance(payload, list):
                for value in payload:
                    nested = _find_delete_key(value)
                    if nested:
                        return nested
            return None

        def handle_layout_change(updated_layout):
            """Callback when user drags/resizes items."""
            st.session_state[layout_state_key] = updated_layout

        # Render the grid with explicit configuration
        with elements(key):
            with dashboard.Grid(
                grid_layout,
                onLayoutChange=handle_layout_change,
            ):
                for item in layout_items:
                    widget_type = item.get("type", "unknown")
                    item_id = str(item["i"])

                    # Display position info for user feedback
                    pos_info = f"x:{item['x']} y:{item['y']} | {item['w']}×{item['h']}"

                    delete_key = f"{delete_state_key_prefix}_{item_id}"

                    # Use mui.Paper as recommended in docs
                    mui.Paper(
                        key=item_id,
                        elevation=3,
                        sx={
                            "display": "flex",
                            "flexDirection": "column",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "height": "100%",
                            "bgcolor": "#EEF2FF",
                            "border": "2px dashed #4F46E5",
                            "borderRadius": "8px",
                            "cursor": "move",
                            "textAlign": "center",
                            "p": 2,
                            "position": "relative",
                        },
                        children=[
                            mui.IconButton(
                                mui.icon.Close(),
                                onClick=sync(delete_key),
                                className="draggable-cancel",
                                key=f"delete_{item_id}",
                                sx={
                                    "position": "absolute",
                                    "top": 2,
                                    "right": 2,
                                    "zIndex": 10,
                                    "bgcolor": "rgba(255,255,255,0.7)",
                                    "&:hover": { "bgcolor": "#ef4444", "color": "white" }
                                }
                            ),
                            mui.Typography(f"📦 {widget_type}", sx={"fontWeight": "bold", "fontSize": "0.85rem"}),
                            mui.Typography(f"({pos_info})", sx={"fontSize": "0.75rem", "color": "text.secondary"})
                        ]
                    )

        # Check if delete was triggered
        widget_to_delete = None
        delete_key_seen = None
        for item in layout_items:
            item_id = str(item["i"])
            delete_key = f"{delete_state_key_prefix}_{item_id}"
            if delete_key in st.session_state:
                delete_key_seen = delete_key
                widget_to_delete = item_id
                st.session_state.pop(delete_key, None)
                break

        if widget_to_delete is None:
            frame_state = st.session_state.get(elements_frame_key)
            if isinstance(frame_state, str):
                try:
                    frame_payload = json.loads(frame_state)
                    delete_key_seen = _find_delete_key(frame_payload)
                    if delete_key_seen:
                        widget_to_delete = delete_key_seen.replace(f"{delete_state_key_prefix}_", "", 1)
                except json.JSONDecodeError:
                    delete_key_seen = None

        if widget_to_delete is not None and delete_key_seen != st.session_state.get(last_delete_key):
            # Remove widget from layout
            new_layout = [item for item in layout_items if str(item["i"]) != str(widget_to_delete)]
            st.session_state[last_delete_key] = delete_key_seen
            return new_layout

        # Check if layout was changed
        if layout_state_key in st.session_state:
            updated = st.session_state[layout_state_key]
            # Merge position updates with original type data
            new_layout = []
            for updated_item in updated:
                item_id = updated_item.get("i") if isinstance(updated_item, dict) else updated_item["i"]
                # Find original to get type
                original = next((x for x in layout_items if str(x["i"]) == str(item_id)), None)
                if original:
                    new_layout.append({
                        "i": item_id,
                        "x": updated_item.get("x", original["x"]) if isinstance(updated_item, dict) else updated_item["x"],
                        "y": updated_item.get("y", original["y"]) if isinstance(updated_item, dict) else updated_item["y"],
                        "w": updated_item.get("w", original["w"]) if isinstance(updated_item, dict) else updated_item["w"],
                        "h": updated_item.get("h", original["h"]) if isinstance(updated_item, dict) else updated_item["h"],
                        "type": original["type"]
                    })
            if new_layout != layout_items:
                return new_layout

        return None

    # --- VIEW MODE: Native Streamlit (Row-based Rendering) ---

    # Sort items by Y, then X to process top-to-bottom, left-to-right
    sorted_items = sorted(layout_items, key=lambda x: (int(x["y"]), int(x["x"])))

    # Group items by Y-coordinate for row-based rendering
    y_groups = {}
    for item in sorted_items:
        y = int(item["y"])
        if y not in y_groups:
            y_groups[y] = []
        y_groups[y].append(item)

    # Process each row group independently
    for row_y in sorted(y_groups.keys()):
        row_items = y_groups[row_y]

        if not row_items:
            continue

        # Sort by X position
        row_items = sorted(row_items, key=lambda x: int(x["x"]))

        # Create columns based on widths
        widths = [int(item["w"]) for item in row_items]

        # If only one item with w>=12, render full width (no columns needed)
        if len(row_items) == 1 and widths[0] >= 12:
            item = row_items[0]
            item_df = widget_data_overrides.get(item["i"], df) if widget_data_overrides else df
            _render_single_widget(item, item_df, quality_df, key_suffix=key_suffix, global_config=global_config)
        else:
            # Multiple items in this row - create columns
            active_cols = st.columns(widths)

            for col, item in zip(active_cols, row_items):
                with col:
                    item_df = widget_data_overrides.get(item["i"], df) if widget_data_overrides else df
                    _render_single_widget(item, item_df, quality_df, key_suffix=key_suffix, global_config=global_config)

    return None

def _render_single_widget(
    item: dict,
    df: pd.DataFrame,
    quality_df: pd.DataFrame = None,
    show_delete: bool = False,
    key_suffix: str = "",
    global_config: dict[str, Any] | None = None
):
    """Helper to render a widget inside a column container.

    Args:
        item: Widget configuration dict
        df: Main dataframe
        quality_df: Quality dataframe (optional)
        show_delete: Whether to show delete button (only in Edit Mode)
        key_suffix: Suffix to append to widget key (e.g. for resetting state)
        global_config: Config to apply to all widgets (merged)
    """
    from app.dashboard.registry import WidgetRegistry

    widget_type = item.get("type", "unknown")
    widget_id = item["i"]
    height_px = item.get("h", 2) * 100 # map grid units to pixels

    # Container for visual separation
    with st.container(border=True):
        try:
            renderer = WidgetRegistry.get_renderer(widget_type)
            # Inject key and height into config
            config = {
                "key": f"{widget_id}{key_suffix}",
                "height": height_px,
            }
            if global_config:
                config.update(global_config)

            # Special handling for Quality widgets which need two dataframes
            if widget_type in ["kpi_quality_score", "chart_quality_gauge"]:
                if quality_df is not None:
                     renderer(df, quality_df, config)
                else:
                     st.warning("Quality data not available for this widget")
            else:
                selection = renderer(df, config)
                # Store selection if available (simplified for now, main.py logic was more complex)
                # Ideally we bubble this up, but for the grid refactor we focus on layout first.

        except Exception as e:
            st.error(f"Error {widget_type}: {e}")


def render_widget_toolbox() -> str | None:
    """Render a toolbox sidebar for adding widgets.

    Returns:
        Widget type to add, or None
    """
    st.sidebar.markdown("### 🧰 Widget Toolbox")

    widget_info = WidgetRegistry.get_widget_info()

    # Group by category
    categories = {}
    for widget_id, info in widget_info.items():
        cat = info["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((widget_id, info["name"]))

    selected_widget = None

    for category, widgets in categories.items():
        with st.sidebar.expander(f"📦 {category.upper()}", expanded=True):
            for widget_id, name in widgets:
                if st.button(f"+ {name}", key=f"add_{widget_id}"):
                    selected_widget = widget_id

    return selected_widget


def add_widget_to_layout(layout_data: dict, widget_type: str) -> dict:
    """Add a new widget to the layout.

    Args:
        layout_data: Current layout
        widget_type: Widget type from registry

    Returns:
        Updated layout
    """
    layout_items = layout_data.get("layout", [])

    # Generate unique ID
    existing_ids = {item["i"] for item in layout_items}
    counter = 1
    while f"widget_{counter}" in existing_ids:
        counter += 1

    new_item = {
        "i": f"widget_{counter}",
        "x": 0,
        "y": len(layout_items) * 4,  # Stack below existing
        "w": 6,
        "h": 4,
        "type": widget_type
    }

    layout_items.append(new_item)
    layout_data["layout"] = layout_items

    return layout_data


def remove_widget_from_layout(layout_data: dict, widget_id: str) -> dict:
    """Remove a widget from the layout.

    Args:
        layout_data: Current layout
        widget_id: Widget instance ID to remove

    Returns:
        Updated layout
    """
    layout_items = layout_data.get("layout", [])
    layout_data["layout"] = [item for item in layout_items if item["i"] != widget_id]
    return layout_data
