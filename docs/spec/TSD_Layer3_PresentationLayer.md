# Technical Specification: Layer 3 - Dynamic Dashboard Engine

**Version:** 2.2  
**Status:** Implemented

## 1. Overview

The dashboard supports two complementary presentation modes:

- a curated **Overview** page for workflow and quality monitoring
- a user-editable **Custom** page backed by persisted layouts and a widget registry

## 2. Architecture

### 2.1 Widget Registry

`app/dashboard/registry.py` maps widget IDs to render functions. The current registry ships:

- 3 KPI widgets
- 7 chart widgets
- 1 table widget

### 2.2 Layout Schema

Custom layouts are stored in `data/config/layouts/*.json` using a 12-column grid model:

```json
{
  "name": "Management View",
  "layout": [
    { "i": "widget_1", "type": "chart_stage_distribution", "x": 0, "y": 0, "w": 12, "h": 4 },
    { "i": "widget_2", "type": "kpi_flow_metrics", "x": 0, "y": 4, "w": 6, "h": 2 },
    { "i": "widget_3", "type": "table_issue_detail_grid", "x": 6, "y": 4, "w": 6, "h": 4 }
  ]
}
```

### 2.3 Grid Engine

`app/dashboard/engine.py` implements a **hybrid rendering strategy**:

1. **Edit Mode**
   - Uses `streamlit-elements`
   - Supports drag-and-drop positioning
   - Supports resize handles
   - Shows lightweight blueprint cards instead of full widgets

2. **View Mode**
   - Uses native Streamlit columns
   - Groups persisted layout items by `y` then `x`
   - Preserves widget interactivity and normal Streamlit behavior

This hybrid model is the current shipped design: edit with `streamlit-elements`, render with native Streamlit.

## 3. User Interface

### 3.1 Active top-level pages

The active navigation in `app/dashboard/main.py` currently exposes:

- `📊 Overview`
- `🎨 Custom`
- `⚡ Admin` when admin access is enabled in session state

### 3.2 Custom view controls

The Custom page supports:

- layout loading from JSON
- edit mode toggle
- drag, resize, and delete while editing
- widget add actions from the sidebar toolbox
- explicit save to disk

### 3.3 Admin operations

The Admin page can:

- run the collector
- run the processor
- clear Streamlit cached data

## 4. Widget Contract

Registered widgets receive:

- a filtered DataFrame
- an optional config dictionary

Common config values include:

| Key | Purpose |
| :---- | :---- |
| `key` | Unique Streamlit widget key |
| `height` | Requested render height |
| widget-specific options | Chart or table behavior overrides |

Quality widgets may also receive `quality_df` in addition to the main analytics DataFrame.

## 5. Current Limitations

- Overview is curated and hard-coded rather than layout-driven
- Edit-mode interactions depend on `streamlit-elements`
