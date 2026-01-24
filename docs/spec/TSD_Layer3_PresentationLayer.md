# **Technical Specification: Layer 3 - Dynamic Dashboard Engine**

**Version:** 2.0

**Scope:** Design for the Dashboard Builder, Widget Registry, and Layout Persistence.

## **1. Tech Stack Additions**

* **Library:** streamlit-elements (Required for Drag & Drop Grid).
* **Storage:** JSON files in data/config/layouts/.

## **2. Component Design**

### **2.1. The Widget Registry (app/dashboard/registry.py)**

A central dispatcher that maps string keys to render functions.

```python
from app.dashboard.widgets import kpis, charts, tables

def get_widget_renderer(widget_type: str):
    mapping = {
        "kpi_bugs": kpis.bug_count,
        "burnup_chart": charts.burnup,
        "aging_boxplot": charts.aging,
        "hygiene_list": tables.hygiene
    }
    return mapping.get(widget_type)
```

### **2.2. The Layout Schema**

Each user view is a JSON file.

| Field | Type | Description |
| :---- | :---- | :---- |
| i | String | Unique Instance ID (e.g., "widget_a1") |
| type | String | Key from Registry (e.g., "kpi_bugs") |
| x | Int | Grid Column Start (0-11) |
| y | Int | Grid Row Start |
| w | Int | Width (in grid units) |
| h | Int | Height (in grid units) |

### **2.3. The Grid Renderer (app/dashboard/engine.py)**

Uses streamlit-elements to render the Bento Grid.

**Algorithm:**

1. **Load Layout:** Read JSON based on selected View from Sidebar.
2. **Initialize Grid:** Create a dashboard.Grid context.
3. **Iterate Items:** For each item in Layout:
   * Look up renderer in Registry.
   * Create a mui.Card.
   * Call the renderer inside the Card context.
4. **Handle State:** If Edit Mode is active, sync layout changes back to st.session_state.

## **3. UX Flow**

### **3.1. Creating a New Dashboard**

1. Click "+" in Sidebar.
2. Name the View (e.g., "Release Status").
3. App creates an empty JSON.
4. User enters "Edit Mode".
5. User selects "Burn Up Chart" from Toolbox.
6. Widget appears on grid.
7. User resizes it to 6x4 units.
8. User clicks Save.

### **3.2. Responsive Design**

* The React-Grid-Layout underlying this architecture automatically reflows to a single column on mobile devices, maintaining the "Bento" integrity without breaking UX.

## **4. Architecture Decision Record (ADR)**

**ADR: Configuration-Driven UI**

* **Decision:** We move from code-defined layouts to data-defined layouts (JSON).
* **Why:** Enables user customization without code changes. Decouples the "What" (Data) from the "Where" (Position).
* **Trade-off:** Slightly higher complexity in the rendering loop (Layer 3) in exchange for massive flexibility. Layer 1 and 2 remain untouched.
