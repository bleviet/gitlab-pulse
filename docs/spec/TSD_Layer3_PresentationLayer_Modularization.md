# Technical Specification: Layer 3 - Widget Modularization

**Version:** 1.1

**Status:** Implemented

## 1. Directory Structure

```
app/dashboard/
├── registry.py                    # Widget dispatcher
├── engine.py                      # Layout CRUD + grid rendering
├── widgets/
│   ├── __init__.py
│   ├── kpis/
│   │   ├── __init__.py
│   │   ├── flow_metrics.py
│   │   ├── stats_kpis.py
│   │   ├── release_metrics.py
│   │   ├── stale_count.py
│   │   └── quality_score.py
│   ├── charts/
│   │   ├── __init__.py
│   │   ├── stage_distribution.py
│   │   ├── aging_boxplot.py
│   │   ├── burnup_velocity.py
│   │   ├── workload_distribution.py
│   │   ├── work_type_distribution.py
│   │   ├── status_donut.py
│   │   ├── quality_gauge.py
│   │   └── error_distribution.py
│   └── tables/
│       ├── __init__.py
│       ├── issue_detail_grid.py
│       ├── stale_issues_list.py
│       ├── quality_action_table.py
│       └── issue_detail_grid.py
└── views/
    ├── overview.py      # Uses widgets
    ├── release.py       # Uses widgets
    ├── stats.py         # Uses widgets
    ├── aging.py         # Uses widgets
    └── hygiene.py       # Uses widgets
```

## 2. Widget Interface

```python
def widget_name(
    df: pd.DataFrame,
    config: dict[str, Any] | None = None
) -> None | dict:
    """Standard widget signature.

    Args:
        df: Filtered DataFrame from Layer 2
        config: Optional configuration dict

    Returns:
        None or selection state for interactive charts
    """
```

## 3. Config Schema

| Key | Type | Purpose |
|-----|------|---------|
| `key` | str | Unique Streamlit key |
| `height` | int | Chart height (px) |
| `title` | str | Override header |
| `group_col` | str | Column to group by |

## 4. Registry Pattern

```python
class WidgetRegistry:
    _registry: dict[str, WidgetRenderer] = {
        "kpi_flow_metrics": flow_metrics,
        "chart_stage_distribution": stage_distribution,
        "table_issue_detail_grid": issue_detail_grid,
        # ...
    }

    @classmethod
    def get_renderer(cls, widget_id: str) -> WidgetRenderer:
        return cls._registry[widget_id]
```

## 5. Definition of Done

- [x] Widget directory structure created
- [x] 16 widgets extracted (4 KPIs, 8 charts, 4 tables)
- [x] All views refactored to use widgets
- [x] Registry implements lookup
- [x] No visual regression
