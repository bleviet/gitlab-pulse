# Technical Specification: Layer 3 - Dynamic Dashboard Engine

**Version:** 2.1

**Status:** Implemented

## 1. Overview

The Dashboard Builder enables users to create custom views by composing widgets from a registry. Layouts are persisted as JSON files.

## 2. Architecture

### 2.1. Widget Registry (`app/dashboard/registry.py`)

Central dispatcher mapping widget IDs to render functions. (See registry.py for full list).

### 2.2. Layout Schema

Layouts stored in `data/config/layouts/*.json`. Uses a 12-column Grid System.

```json
{
  "name": "Management View",
  "layout": [
    // Mosaic Layout: Tall widget on left, stacked widgets on right
    {"i": "w1", "type": "chart_aging_boxplot", "x": 0, "y": 0, "w": 6, "h": 4},
    {"i": "w2", "type": "kpi_flow_metrics",    "x": 6, "y": 0, "w": 6, "h": 2},
    {"i": "w3", "type": "kpi_quality_score",   "x": 6, "y": 2, "w": 6, "h": 2}
  ]
}
```

### 2.3. Grid Engine (`app/dashboard/engine.py`)

The engine uses a **Hybrid Rendering Strategy**:

1.  **Edit Mode (Blueprint):**
    -   Uses `streamlit-elements` (React-Grid-Layout) to render a visual "Blueprint" of the dashboard.
    -   Displays simplified "Cards" representing widgets.
    -   Allows **Drag-and-Drop** positioning and **Resizing**.
    -   Updates the internal `layout` state in real-time.

2.  **View Mode (Native Render):**
    -   Converts the grid coordinates `(x, y, w, h)` into native Streamlit structures.
    -   **Mosaic Detection:** Identifies vertical columns of widgets.
        -   *Example:* If Widget A is at `x=0, w=6` and Widget B/C are at `x=6, w=6`, it creates 2 main columns.
        -   Col 1 renders Widget A (height handled via `st.container(height=...)` or natural height).
        -   Col 2 renders Widget B then Widget C vertically.
    -   **Fallback:** Row-based rendering for linear layouts.

## 3. User Interface

### 3.1. Interactive Grid (Edit Mode)
-   **Toggle:** "✏️ Edit Layout" button in sidebar.
-   **Visuals:**
    -   Widgets appear as Draggable Cards with handles.
    -   "Empty" grid spaces are visible hints.
-   **Actions:**
    -   **Resize:** Grab corner to span multiple rows/columns.
    -   **Swap:** Drag Widget A over Widget B to swap positions.
    -   **Remove:** 'X' button on card corner.
-   **Persist:** "Save Changes" button commits JSON to disk.

### 3.2. Widget Toolbox
-   Sidebar panel listing available widgets by category (KPIs, Charts, Tables).
-   "Add +" button injects widget into the first available grid space.

## 4. Widget Contract

Widgets must support flexible sizing to fit grid containers:
-   `height`: passed from grid row-span logic (e.g. 1 unit = 150px).
-   `use_container_width`: always True.

## 5. Implementation Notes

-   **Mosaic Support:** The rendering algorithm must prioritize "Vertical Stacks" over "Horizontal Rows" to support the "Tall Left, Stacked Right" pattern requested.
-   **Row Units:** Base row height set to ~150px. Widget height `h=2` -> 300px container.
-   **Responsive:** Grid collapses to single column on mobile, but preserves relative order.
