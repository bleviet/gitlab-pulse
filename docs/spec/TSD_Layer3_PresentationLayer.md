# Technical Specification: Layer 3 - Dynamic Dashboard Engine

**Version:** 2.1

**Status:** Implemented

## 1. Overview

The Dashboard Builder enables users to create custom views by composing widgets from a registry. Layouts are persisted as JSON files.

## 2. Architecture

### 2.1. Widget Registry (`app/dashboard/registry.py`)

Central dispatcher mapping widget IDs to render functions.

| Category | Widget ID | Function |
|----------|-----------|----------|
| KPI | `kpi_flow_metrics` | Flow metrics (WIP, Efficiency, Backlog) |
| KPI | `kpi_stats` | Statistics KPIs |
| KPI | `kpi_stale_count` | Stale issue count |
| KPI | `kpi_quality_score` | Quality percentage |
| Chart | `chart_stage_distribution` | Horizontal bar by stage |
| Chart | `chart_aging_boxplot` | Age distribution boxplot |
| Chart | `chart_burnup_velocity` | Burnup + velocity chart |
| Chart | `chart_workload_distribution` | Assignee workload |
| Chart | `chart_work_type_distribution` | Issue type breakdown |
| Chart | `chart_status_donut` | Open/Closed donut |
| Chart | `chart_quality_gauge` | Quality score gauge |
| Chart | `chart_error_distribution` | Error code distribution |
| Table | `table_issue_detail_grid` | Issue detail grid |
| Table | `table_stale_issues_list` | Stale issues list |
| Table | `table_quality_action` | Quality action items |
| Table | `table_capacity_grid` | Capacity planning grid |

### 2.2. Layout Schema

Layouts stored in `data/config/layouts/*.json`:

```json
{
  "name": "My Dashboard",
  "description": "Custom view",
  "layout": [
    {"i": "widget_1", "type": "kpi_flow_metrics", "x": 0, "y": 0, "w": 12, "h": 2},
    {"i": "widget_2", "type": "chart_stage_distribution", "x": 0, "y": 2, "w": 6, "h": 4}
  ]
}
```

### 2.3. Grid Engine (`app/dashboard/engine.py`)

Functions:
- `load_layout(name)` - Load JSON layout
- `save_layout(name, data)` - Persist layout
- `delete_layout(name)` - Remove layout (protected: default)
- `create_layout(name)` - Create new empty layout
- `add_widget_to_layout(data, type)` - Add widget
- `remove_widget_from_layout(data, id)` - Remove widget

## 3. User Interface

### 3.1. Sidebar Controls

Located at top of sidebar (immediately visible):
- **View dropdown** - Select layout
- **➕ button** - Create new view
- **🗑️ button** - Delete view (disabled for default)
- **✏️ Edit Mode toggle** - Enable editing

### 3.2. Widget Toolbox

Visible when Edit Mode is on:
- **📊 KPIs** - 4 widgets
- **📈 Charts** - 8 widgets
- **📋 Tables** - 4 widgets

### 3.3. Custom View Tab

Navigation: **🎨 Custom**
- Renders widgets from selected layout
- Edit mode: ✕ buttons to remove widgets
- Save/Exit Edit buttons in header

## 4. Widget Contract

```python
def widget_function(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> None:
```

Config keys:
- `key` - Unique Streamlit key (required for multiple instances)
- `height` - Chart height in pixels
- `title` - Override header

## 5. Implementation Notes

- Widgets use native Streamlit rendering (not streamlit-elements)
- Quality widgets require both `valid_df` and `quality_df`
- Chart keys derived from `config["key"]` to prevent conflicts
