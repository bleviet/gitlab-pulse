# Technical Specification: Layer 3 - Widget Modularization

**Version:** 1.2  
**Status:** Implemented

## 1. Current Directory Structure

```text
app/dashboard/
├── registry.py
├── engine.py
├── data_loader.py
├── sidebar.py
├── views/
│   └── admin.py
│   └── overview.py
└── widgets/
    ├── kpis/
    │   ├── flow_metrics.py
    │   ├── quality_score.py
    │   └── stale_count.py
    ├── charts/
    │   ├── burnup_velocity.py
    │   ├── error_distribution.py
    │   ├── milestone_timeline.py
    │   ├── quality_gauge.py
    │   ├── stage_distribution.py
    │   ├── status_donut.py
    │   ├── workload_distribution.py
    │   └── work_type_distribution.py
    ├── tables/
    │   └── issue_detail_grid.py
    └── features/
        └── ai_assistant.py
```

## 2. Current Registry Surface

The current widget registry exposes 11 layout-builder widgets:

- **KPIs:** `kpi_flow_metrics`, `kpi_stale_count`, `kpi_quality_score`
- **Charts:** `chart_stage_distribution`, `chart_burnup_velocity`, `chart_workload_distribution`, `chart_work_type_distribution`, `chart_status_donut`, `chart_quality_gauge`, `chart_error_distribution`, `chart_milestone_timeline`
- **Tables:** `table_issue_detail_grid`

The AI assistant is modularized under `widgets/features/`, but it is not a layout-builder registry widget today. It is used from the overview drill-down flow.

## 3. Widget Interface

The current registry contract is:

```python
def widget_name(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None,
) -> None | dict:
    ...
```

Some widgets return selection data for interactive filtering. Quality widgets use a specialized call path that also receives the quality DataFrame.

## 4. What Modularization Achieved

- widget rendering is isolated from page wiring
- the layout engine can instantiate widgets by ID
- the custom dashboard builder no longer depends on one-off page-specific rendering logic
- overview-specific composition can still remain curated when needed

## 5. Current Implementation Notes

- The modularization effort is complete enough for the shipped custom layout builder
- Not every dashboard surface is registry-driven; the Overview page still composes panels directly
