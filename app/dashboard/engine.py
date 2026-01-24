"""Dashboard Grid Engine for Layer 3.

Renders widgets in a drag-and-drop grid using streamlit-elements.
Supports View Mode (locked) and Edit Mode (draggable/resizable).
"""

import json
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from streamlit_elements import elements, dashboard, mui

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
    key: str = "dashboard_grid"
) -> dict | None:
    """Render widgets in a grid layout using streamlit-elements.

    Args:
        df: DataFrame with issue data
        layout_data: Layout dictionary with widget positions
        edit_mode: If True, widgets are draggable and resizable
        key: Unique key for the elements context

    Returns:
        Updated layout if in edit mode and changed, None otherwise
    """
    layout_items = layout_data.get("layout", [])

    if not layout_items:
        st.info("No widgets in this layout. Switch to Edit Mode to add widgets.")
        return None

    # Convert layout items to dashboard format
    grid_layout = []
    for item in layout_items:
        grid_layout.append(
            dashboard.Item(
                i=item["i"],
                x=item["x"],
                y=item["y"],
                w=item["w"],
                h=item["h"],
                isDraggable=edit_mode,
                isResizable=edit_mode,
            )
        )

    # Track layout changes in session state
    layout_key = f"{key}_layout"
    if layout_key not in st.session_state:
        st.session_state[layout_key] = layout_items

    def handle_layout_change(updated_layout):
        """Callback when layout changes in edit mode."""
        st.session_state[layout_key] = updated_layout

    # Render the grid
    with elements(key):
        with dashboard.Grid(
            grid_layout,
            onLayoutChange=handle_layout_change if edit_mode else None,
            draggableHandle=".drag-handle" if edit_mode else None,
            cols=12,
            rowHeight=60,
        ):
            for item in layout_items:
                widget_type = item.get("type")
                item_id = item["i"]

                with mui.Card(
                    key=item_id,
                    sx={
                        "display": "flex",
                        "flexDirection": "column",
                        "height": "100%",
                        "bgcolor": "background.paper",
                        "borderRadius": 2,
                        "overflow": "hidden",
                    }
                ):
                    # Header with drag handle in edit mode
                    if edit_mode:
                        with mui.Box(
                            className="drag-handle",
                            sx={
                                "cursor": "move",
                                "bgcolor": "primary.main",
                                "color": "white",
                                "px": 2,
                                "py": 0.5,
                                "display": "flex",
                                "alignItems": "center",
                            }
                        ):
                            mui.Icon("drag_indicator", sx={"mr": 1})
                            mui.Typography(widget_type, variant="caption")

                    # Widget content
                    with mui.CardContent(sx={"flexGrow": 1, "overflow": "auto"}):
                        try:
                            renderer = WidgetRegistry.get_renderer(widget_type)
                            # Note: We can't directly call Streamlit widgets inside
                            # streamlit-elements cards. We'll render a placeholder.
                            mui.Typography(
                                f"Widget: {widget_type}",
                                variant="body2",
                                color="text.secondary"
                            )
                        except ValueError:
                            mui.Typography(
                                f"Unknown widget: {widget_type}",
                                color="error"
                            )

    # Return updated layout if changed
    if edit_mode and st.session_state.get(layout_key):
        return st.session_state[layout_key]

    return None


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
