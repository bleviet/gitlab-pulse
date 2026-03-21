# Theme Consolidation Refactoring Plan

## Problem Statement

The dashboard's color & theming system has grown organically across five overlapping API surfaces, making it **hard to maintain, hard to follow, and prone to bugs** (like the zebra-stripe color that never changed in dark mode). This plan proposes a ground-up simplification that leverages Streamlit's native `[theme.light]` / `[theme.dark]` configuration as the single source of truth for UI chrome, while keeping a lean Python-side palette for **semantic domain colors** only (issue types, severities, stages, chart series).

---

## Current Architecture — What's Wrong

### 1. Five Overlapping API Surfaces in `theme.py`

| Surface | Lines | Purpose | Problem |
|---|---|---|---|
| `ThemeAwareDict` + `PALETTE` | 68–203 | Mutable dict that swaps light/dark at runtime | Complex, 47 color keys duplicated across two dicts. Requires `_sync_semantic_palette_maps()` to keep secondary dicts in sync. |
| `SEVERITY_COLORS`, `ISSUE_TYPE_COLORS`, `STAGE_TYPE_COLORS` | 205–252 | Semantic color maps | Three more `ThemeAwareDict` instances that mirror subsets of `PALETTE`. Sync logic is error-prone. |
| `_THEME_MODE_TOKENS` | 368–397 | CSS injection tokens | Duplicates values already defined in `config.toml` (`accent`, `text`, `border`, etc.). |
| `get_active_theme()` | 400–405 | Returns dict payload for callers | Yet another dict format. Only used for backward compat. |
| `plotly_layout()` / `get_plotly_font_color()` / `plotly_bar_trace_style()` | 435–522 | Plotly helpers | Good idea, but 5 chart widgets bypass it and manually construct layouts with `FONT_FAMILY` + `get_plotly_font_color()` anyway. |

### 2. `config.toml` ↔ Python Duplication

Colors like `primaryColor`, `backgroundColor`, `textColor`, `borderColor` are defined in both `config.toml` **and** in `_THEME_MODE_TOKENS` / `_PALETTE_LIGHT` / `_PALETTE_DARK`. When a designer changes a color, they must update it in two (or three) places.

### 3. Scattered Consumer Patterns

| Pattern | Files | Issue |
|---|---|---|
| `from theme import PALETTE` | 9 files | Directly accessed by key. Some alias it as `COLORS`. |
| `from theme import PALETTE as COLORS` | 3 files | Inconsistent aliasing hurts readability. |
| `from theme import FONT_FAMILY, get_plotly_font_color` | 5 files | Widgets that build Plotly layouts manually instead of using `plotly_layout()`. |
| `colors=colors` dict pass-through | 6 views | `main.py` calls `apply_rule_color_overrides()`, passes flat dict to every view. Views mostly ignore it — they import `PALETTE` directly anyway. |

### 4. YAML Rule Color Overrides — Overly Complex Reset Flow

`apply_rule_color_overrides()` does `_reset_palette_to_defaults()` → mutate `_PALETTE_LIGHT` / `_PALETTE_DARK` → `_sync_semantic_palette_maps()`. This mutation-based approach means the module's global state changes on every call, and the base/reset dicts add more duplication.

---

## Proposed Architecture

### Design Principles

1. **`config.toml` owns UI chrome.** Background, text, border, primary, sidebar — all natively handled by Streamlit. No Python duplication.
2. **Python owns semantic domain colors only.** Issue types (`Bug`, `Feature`), severities (`Critical`, `High`), stages (`active`, `waiting`), and chart series colors (`burnup_feature_fill`, `ms_complete`, etc.).
3. **One function to get colors, no global mutable state.** Replace `ThemeAwareDict` with a simple function `get_palette() -> dict[str, str]` that reads the current mode and returns the correct immutable dict.
4. **All Plotly charts go through `plotly_layout()`.** No more manual `font=dict(family=..., color=...)` scattered across widgets.
5. **Remove the `colors=colors` pass-through.** Widgets/ views call `get_palette()` directly when they need a semantic color. The YAML override is applied once at startup and baked into the palette data.

### File-Level Changes

---

### Component 1: Core Theme Module

#### [MODIFY] [theme.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/theme.py)

**Delete entirely and rewrite.** Target ≈ 200 lines (down from 620).

**New structure:**

```python
"""Centralized Dashboard Theme Module.

UI chrome colors (background, text, borders) are owned by
`.streamlit/config.toml`. This module provides:
  - Semantic domain color palettes (issue types, severities, stages, chart series)
  - Plotly layout helpers that read native Streamlit theme options
  - Minimal CSS injection for effects not expressible in config.toml
"""

# ── 1. Mode detection ──────────────────────────────────────────────
def get_active_theme_mode() -> str: ...  # keep as-is (reads st.get_option)

# ── 2. Semantic palettes ───────────────────────────────────────────
_SEMANTIC_LIGHT: dict[str, str] = { ... }   # ~30 keys: domain colors only
_SEMANTIC_DARK:  dict[str, str] = { ... }   # matching dark variants

def get_palette() -> dict[str, str]:
    """Return the active semantic palette (immutable copy)."""
    ...

# Convenience accessors (thin wrappers around get_palette)
def get_severity_colors() -> dict[str, str]: ...
def get_issue_type_colors() -> dict[str, str]: ...
def get_stage_colors() -> dict[str, str]: ...

# ── 3. YAML rule color overrides ───────────────────────────────────
def apply_rule_color_overrides(overrides: dict | None) -> None:
    """Merge YAML color overrides into the semantic palettes. Called once at startup."""
    ...

# ── 4. Plotly helpers ──────────────────────────────────────────────
def plotly_layout(...) -> dict[str, Any]:  # keep, but read font/colors from st.get_option
    ...

def plotly_bar_trace_style() -> dict[str, Any]:  # keep
    ...

# ── 5. Global CSS ─────────────────────────────────────────────────
def get_global_css() -> str:
    """Minimal CSS: metric card gradients, radio tabs, scrollbar.
    Read ALL color values from st.get_option — no duplicate constants.
    """
    ...
```

**Key deletions:**
- `ThemeAwareDict` class (replaced by `get_palette()` function)
- `_PALETTE_LIGHT` / `_PALETTE_DARK` (replaced by `_SEMANTIC_LIGHT` / `_SEMANTIC_DARK` with ~30 domain-only keys instead of 47)
- `_BASE_PALETTE_LIGHT` / `_BASE_PALETTE_DARK` (no reset needed)
- `PALETTE`, `SEVERITY_COLORS`, `ISSUE_TYPE_COLORS`, `STAGE_TYPE_COLORS` module-level globals
- `_SEVERITY_TO_PALETTE_KEY`, `_ISSUE_TYPE_TO_PALETTE_KEY`, `_STAGE_TYPE_TO_PALETTE_KEY` mapping dicts
- `_sync_semantic_palette_maps()`, `_reset_palette_to_defaults()`, `_normalize_color_mapping()`
- `_THEME_MODE_TOKENS` dict (values will be read from `st.get_option` at call time)
- `get_active_theme()` backward-compat function
- `FONT_FAMILY` constant (read from `st.get_option("theme.font")` or fallback)
- `FONT_IMPORT_URL` unused constant

**What moves to `config.toml`:**
- `surface`, `surface_hover`, `border`, `shadow`, `shadow_hover` → these are `backgroundColor`, `secondaryBackgroundColor`, `borderColor` — already in config.toml.
- `sidebar_bg`, `sidebar_bg_alt`, `sidebar_text`, `sidebar_text_muted`, `sidebar_border`, `sidebar_accent` → already in `[theme.light.sidebar]` / `[theme.dark.sidebar]`.

**What stays in Python (semantic domain colors only):**
- Issue types: `bug`, `feature`, `task`, `epic`
- Severities: `critical`, `high`, `medium`, `low`, `unset`
- Priorities: `p1`, `p2`, `p3`
- Stages: `active`, `waiting`, `completed`, `stale`
- Chart series: `burnup_feature_fill`, `burnup_feature_area`, `burnup_bug_fill`, etc.
- Milestone chart: `ms_complete`, `ms_incomplete`, `ms_on_track`, `ms_overdue`, `ms_highlight`
- Flow chart: `opened`, `closed`, `scope_line`

---

### Component 2: Consumer Migration (Charts)

All 11 chart widgets in `app/dashboard/widgets/charts/` will be updated.

#### Widgets already using `plotly_layout()` — minimal change

These 7 widgets already use `plotly_layout()`. They only need import changes:

- [aging_boxplot.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/widgets/charts/aging_boxplot.py) — replace `PALETTE as COLORS` → `get_palette`; replace `STAGE_TYPE_COLORS` → `get_stage_colors()`
- [daily_activity_bar.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/widgets/charts/daily_activity_bar.py) — replace `PALETTE` → `get_palette()`
- [error_distribution.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/widgets/charts/error_distribution.py) — replace `PALETTE` → `get_palette()`
- [quality_gauge.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/widgets/charts/quality_gauge.py) — replace `PALETTE` → `get_palette()`
- [status_donut.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/widgets/charts/status_donut.py) — replace `PALETTE` → `get_palette()`
- [work_type_distribution.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/widgets/charts/work_type_distribution.py) — replace `ISSUE_TYPE_COLORS` → `get_issue_type_colors()`
- [workload_distribution.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/widgets/charts/workload_distribution.py) — replace `PALETTE as COLORS` → `get_palette()`

#### Widgets with manual Plotly layouts — moderate change

These 3 widgets build `fig.update_layout(font=dict(family=FONT_FAMILY, color=get_plotly_font_color()), ...)` manually. They will be refactored to use `plotly_layout()`:

- [burnup_velocity.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/widgets/charts/burnup_velocity.py) — replace manual layout with `plotly_layout()`; drop `FONT_FAMILY`, `get_plotly_font_color` imports
- [milestone_timeline.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/widgets/charts/milestone_timeline.py) — same treatment
- [stage_distribution.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/widgets/charts/stage_distribution.py) — replace `PALETTE as COLORS` + manual font references; use `plotly_layout()` + `get_palette()`

---

### Component 3: Consumer Migration (Tables & Utilities)

#### [MODIFY] [issue_detail_grid.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/widgets/tables/issue_detail_grid.py)

Replace `PALETTE["surface_hover"]` → `get_palette()["surface_hover"]`.

> [!NOTE]
> `surface_hover` stays in the semantic palette for now because Streamlit's `secondaryBackgroundColor` serves a different purpose (widget input backgrounds). The zebra stripe needs a mid-tone between `backgroundColor` and `secondaryBackgroundColor`, which is a domain concern.

#### [MODIFY] [utils.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/utils.py)

Replace `from app.dashboard.theme import PALETTE` and `PALETTE.get(key, default)` in `get_semantic_color()` → `from app.dashboard.theme import get_palette` and `get_palette().get(key, default)`.

---

### Component 4: View Layer Cleanup

#### [MODIFY] [main.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/main.py)

- `apply_rule_color_overrides(default_rule.colors)` stays (called once at startup, now mutates `_SEMANTIC_*` dicts).
- **Remove** the `colors` return value and the `colors=colors` pass-through to all view functions.

#### [MODIFY] All views that accept `colors` parameter

The following files will have `colors: dict[str, str] | None = None` removed from their render signatures:

- [overview.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/views/overview.py)
- [hygiene.py](file:///home/balevision/workspace/bleviet/gitlab-insight/app/dashboard/views/hygiene.py)

If any view internally uses the `colors` dict, it will be replaced with `get_palette()` call.

### Component 5: `get_global_css()` Simplification

The CSS injection function currently uses `_THEME_MODE_TOKENS` to hardcode colors. It will be rewritten to read from `st.get_option()`:

```python
def get_global_css() -> str:
    """Minimal CSS for effects not expressible in config.toml."""
    bg = st.get_option("theme.backgroundColor") or "#fdfdf8"
    secondary_bg = st.get_option("theme.secondaryBackgroundColor") or "#ecebe3"
    text_color = st.get_option("theme.textColor") or "#3d3a2a"
    text_muted = _with_alpha(text_color, 0.6, "#6b695e")
    primary = st.get_option("theme.primaryColor") or "#cb785c"
    border = st.get_option("theme.borderColor") or "#d3d2ca"
    # ... build CSS using these resolved values
```

This eliminates `_THEME_MODE_TOKENS` entirely.

---

### Component 6: Documentation Updates

#### [MODIFY] [GUIDE_Developer.md](file:///home/balevision/workspace/bleviet/gitlab-insight/docs/guidelines/GUIDE_Developer.md)

Update section **9.2. Native Theming** to document the new API:

- `get_palette()` for semantic domain colors
- `get_severity_colors()`, `get_issue_type_colors()`, `get_stage_colors()` convenience accessors
- `plotly_layout()` as the mandatory way to build Plotly layouts
- Rule: no direct `st.get_option("theme.*")` calls outside `theme.py`

---

## Summary of Impact

| Metric | Before | After |
|---|---|---|
| `theme.py` lines | ~620 | ~200 |
| Module-level mutable globals | 7 (`PALETTE`, `SEVERITY_COLORS`, `ISSUE_TYPE_COLORS`, `STAGE_TYPE_COLORS`, `_PALETTE_LIGHT`, `_PALETTE_DARK`, `_THEME_MODE_TOKENS`) | 2 (`_SEMANTIC_LIGHT`, `_SEMANTIC_DARK`) |
| Duplicate color definitions (`config.toml` ↔ Python) | ~15 keys duplicated | 0 |
| Import patterns for consumers | 5 different patterns | 1 (`from theme import get_palette, plotly_layout`) |
| Classes | 1 (`ThemeAwareDict`) | 0 |
| Files touched | — | ~22 files |

---

## Verification Plan

### Automated Tests

No existing theme-related tests exist. The refactoring is primarily a rename/restructure, so the risk is **import errors and missing keys at runtime**.

```bash
# 1. Import smoke test — verify no ImportError across the codebase
uv run python -c "
from app.dashboard.theme import get_palette, get_severity_colors, get_issue_type_colors, get_stage_colors, plotly_layout, plotly_bar_trace_style, get_global_css, get_active_theme_mode, apply_rule_color_overrides
print('All theme imports OK')
palette = get_palette()
print(f'Palette has {len(palette)} keys')
"

# 2. Verify all widget modules import cleanly
uv run python -c "
import importlib, sys
modules = [
    'app.dashboard.widgets.charts.burnup_velocity',
    'app.dashboard.widgets.charts.error_distribution',
    'app.dashboard.widgets.charts.milestone_timeline',
    'app.dashboard.widgets.charts.quality_gauge',
    'app.dashboard.widgets.charts.stage_distribution',
    'app.dashboard.widgets.charts.status_donut',
    'app.dashboard.widgets.charts.work_type_distribution',
    'app.dashboard.widgets.charts.workload_distribution',
    'app.dashboard.widgets.tables.issue_detail_grid',
    'app.dashboard.utils',
]
for m in modules:
    importlib.import_module(m)
    print(f'  ✓ {m}')
print('All widget imports OK')
"

# 3. Run existing tests to catch regressions
uv run pytest tests/ -v
```

### Manual Verification

> [!IMPORTANT]
> Because this is a visual theming refactor, the most reliable verification is **visual inspection** of the running dashboard in both light and dark modes.

1. **Start the dashboard:** `uv run streamlit run app/dashboard/main.py`
2. **Light mode check:**
   - Verify metric cards have correct gradient backgrounds and hover effects
   - Verify chart colors match expected semantic palette (green for features, red for bugs, etc.)
   - Verify zebra stripes in issue detail grid use the correct light tone
   - Verify radio tabs have correct accent highlighting
3. **Dark mode check** (via ⋮ → Settings → Theme → Dark):
   - Same checks as light mode but with dark palette
   - Specifically verify the zebra-stripe bug is still fixed (should not show `#ecebe3`)
   - Verify Plotly chart backgrounds are transparent and text/grid colors adapt
4. **Verify no console errors** in the browser developer tools
