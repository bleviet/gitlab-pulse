# Reference: Layer 3 FastAPI + React/TypeScript Implementation

This document catalogs every backend module, API endpoint, frontend module, URL parameter, configuration variable, test suite, and removed artifact on branch `feat/fastapi-react-dashboard`.

## 1. Backend Modules (`app/dashboard/`)

| File | Purpose | Key Symbols |
|---|---|---|
| `app/dashboard/__init__.py` | Package marker | — |
| `app/dashboard/__main__.py` | Uvicorn CLI entry point (`--host`, `--port`, `--reload`) | `main()` |
| `app/dashboard/schemas.py` | Frozen Pydantic v2 request/response DTOs | `IssueItem`, `LabelStyle`, `StageMeta`, `ThemePalettes`, `SyncStatus`, `FilterOptions`, `DashboardPayload`, `AdminLoginRequest`, `AdminStatusResponse`, `AdminJobResponse`, `HealthResponse` |
| `app/dashboard/data_loader.py` | Parquet and sync-state readers with UTC normalization | `load_valid_issues()`, `load_labels()`, `get_sync_status()` |
| `app/dashboard/utils.py` | Assignee/label normalization, quality signals, hierarchy DFS sort | `normalize_assignee_labels()`, `normalize_issue_labels()`, `mixed_classification_hints()`, `compute_issue_signals_and_hints()`, `is_local_issue_url()`, `sort_hierarchy()`, `compute_quality_summary()` |
| `app/dashboard/palettes.py` | Light/dark semantic color maps with YAML rule overrides | `resolve_palettes()` |
| `app/dashboard/service.py` | Context collapsing, payload construction, `st_mtime_ns` cache | `DashboardService` (`get_dashboard_payload()`, `clear_cache()`) |
| `app/dashboard/admin.py` | Cookie-authenticated admin router | `create_admin_router()`, `ADMIN_COOKIE_NAME` |
| `app/dashboard/server.py` | FastAPI app factory, GZip, CORS, SPA fallback serving | `create_app()`, `app` |

### 1.1 `DashboardService` Cache Key

`DashboardService._compute_mtime_key()` records `(path, st_mtime_ns)` for:
- `data/analytics/issues_valid.parquet`
- `data/state/sync_state.json`
- `data/processed/labels_*.parquet`
- `app/config/rules/*.yaml`

Heavy raw columns (`description`, `notes`) are omitted from `IssueItem` in `DashboardPayload`. Exploded context rows sharing the same `id` are collapsed into a single `IssueItem` with a deduplicated `contexts: list[str]`.

## 2. HTTP API Endpoints

| Method | Path | Auth | Request Body | Response Model / Behavior |
|---|---|---|---|---|
| `GET` | `/api/health` | None | — | `HealthResponse` (`{"status": "ok"}`) |
| `GET` | `/api/dashboard` | None | — | `DashboardPayload` |
| `GET` | `/api/admin/status` | Optional cookie | — | `AdminStatusResponse` (`{"authenticated": bool}`) |
| `POST` | `/api/admin/login` | None | `AdminLoginRequest` (`{"password": str}`) | `200` sets `HttpOnly`, `SameSite=lax` cookie `pulse_admin_session`; `401` on mismatch |
| `POST` | `/api/admin/logout` | Optional cookie | — | `AdminStatusResponse` (`authenticated: false`), revokes token and deletes cookie |
| `POST` | `/api/admin/run/collector` | Cookie required (`401`) | — | `AdminJobResponse` executing `app/collector/orchestrator.py`; clears cache on `returncode == 0` |
| `POST` | `/api/admin/run/processor` | Cookie required (`401`) | — | `AdminJobResponse` executing `app/processor/main.py`; clears cache on `returncode == 0` |
| `POST` | `/api/admin/clear-cache` | Cookie required (`401`) | — | `{"ok": true}` and invalidates `DashboardService` cache |
| `GET` | `/`, `/{full_path:path}` | None | — | Serves `frontend/dist/index.html` (or static file); returns `404` JSON for unknown `/api/*` paths |

## 3. Frontend Modules (`frontend/`)

### 3.1 Configuration & Assets
- `frontend/package.json`: React 19, TypeScript 5.8, Vite 7, Vitest 3, `@tanstack/react-table` 8, `lucide-react`.
- `frontend/vite.config.ts`: dev server on `:5173` proxying `/api` to `http://127.0.0.1:8501`, Vitest `jsdom` environment.
- `frontend/tsconfig.json`: `strict: true`, `noUnusedLocals: true`, `noUnusedParameters: true`.
- `frontend/index.html`: sets initial `document.documentElement.dataset.theme` synchronously from `localStorage` (`pulse_theme`, default `"dark"`).
- `frontend/public/static/`: self-hosted fonts (`Manrope-VariableFont.woff2`, `SpaceGrotesk-VariableFont_wght.ttf`, `SpaceMono-Regular.ttf`, `SpaceMono-Bold.ttf`, license files), `logo.svg`, and `favicon.png`.

### 3.2 Styles (`frontend/src/styles/`)
- `fonts.css`: `@font-face` declarations for `"Manrope"`, `"Space Grotesk"`, and `"Space Mono"` served from `/static/`.
- `tokens.css`: `:root` (dark default) and `[data-theme="light"]` CSS custom properties following bahonavi design tokens (`--bg`, `--bg-card`, `--bg-raise`, `--surface`, `--line`, `--line-strong`, `--text`, `--heading`, `--muted`, `--accent`, `--brand`, `--brand-2`, `--grad`, `--chart-1..8`, `--chart-bg`, `--chart-grid`, `--chart-axis`, `--chart-label`, `--chart-tooltip-bg`).
- `global.css`: bahonavi corner-glow and 72px blueprint-grid background, sticky topbar/panel/lane-header rules, scope/popover/modal styles, table/board card styling, `:focus-visible` outlines, and `prefers-reduced-motion` guards.

### 3.3 Pure Domain Modules (`frontend/src/lib/`)

| File | Responsibility | Key Exports |
|---|---|---|
| `types.ts` | TypeScript interfaces matching API DTOs and UI state | `IssueItem`, `DashboardPayload`, `GlobalFilters`, `IssueFacets`, `IssueViewMode`, `ThemeMode`, `ActiveChartId` |
| `colors.ts` | Priority, issue-type, & contrast color resolution | `getPriorityColor`, `getIssueTypeColor`, `buildPriorityColorMap`, `hexWithAlpha`, `contrastTextForHex` |
| `search.ts` | Multi-token exact search + LCS fuzzy fallback (`<=4: 0.90`, `<=8: 0.82`, `>8: 0.72`) | `normalizeSearchText`, `similarityRatio`, `filterIssuesBySearch` |
| `scopeSearch.ts` | Fuzzy scoring and multi-dimension combined quick-apply matching for `ScopeBar` | `scoreScopeCandidate`, `buildScopeSuggestions` |
| `facets.ts` | Global/facet filtering, cascading options, chip construction, URL state serialization | `applyPreMilestoneFilters`, `applyGlobalFilters`, `applyFacets`, `buildFacetChips`, `deriveScopedFilterOptions`, `resolvePresetDates`, `withoutFacet`, `parseGlobalFiltersUrl`, `parseUrlState`, `buildUrlSearch` |
| `summary.ts` | Compact summary pill groups (`Flow`, `Open by priority`, `Hints`) | `buildSummaryGroups` |
| `timeline.ts` | Milestone status grouping for dated milestones, natural version sort, month ticks, unscheduled-milestone summary | `naturalCompare`, `buildMilestoneTimelineData`, `buildMonthTicks`, `buildUnscheduledMilestonesData` |
| `board.ts` | Workflow stage ordering, lane mapping, default/hierarchy sorting, lane priority mix | `getOverviewStages`, `getWorkflowStages`, `getBoardLanes`, `sortIssuesDefault`, `sortIssuesHierarchy`, `computeLanePriorityCounts` |
| `analytics.ts` | Client-side aggregations for Analytics charts | `buildPriorityDonutData`, `buildIssueTypeDonutData`, `buildQualitySignalsData`, `buildDailyVelocityData`, `buildStagePriorityBars` |
| `api.ts` | Typed `fetch` wrappers with `credentials: "include"` | `fetchDashboard`, `fetchAdminStatus`, `adminLogin`, `adminLogout`, `runCollector`, `runProcessor`, `clearDashboardCache` |

### 3.4 React Components (`frontend/src/components/`)

| File | Responsibility |
|---|---|
| `charts/ChartTooltip.tsx` | Floating tooltip shared by all charts; rendered into `document.body` via a portal so scrolling chart containers cannot clip it, placed below and right of the cursor and flipped (`placeTooltip`) when it would leave the viewport |
| `charts/ReleaseTimeline.tsx` | Responsive SVG milestone rail (`compact` and `analytics` variants, `NOW` marker, month ticks on UTC month starts, clickable milestone pins for dated milestones, fixed-width tray with the unscheduled milestone count) |
| `charts/PriorityDonut.tsx` | Responsive SVG donut with clickable slices, clickable center total, and compact clickable legend (used for Open Priority and Open Issue Type) |
| `charts/UnscheduledMilestonesChart.tsx` | Horizontal bars of open issues per milestone without a due date (`Total`, `Priority`, or `Type` breakdown, at most 6 rows, hidden-closed footnote); rows set the milestone filter; rendered in the wide rail or in a popover from the release rail tray |
| `charts/QualitySignalsChart.tsx` | Horizontal bar chart for `MISSING_MILESTONE`, `UNASSIGNED_OWNER`, and `MIXED_CLASSIFICATION` (`Open Hints`) |
| `charts/DailyVelocityChart.tsx` | 7-day dual-line SVG chart (`New` vs. `Closed`) with historical anchoring and clickable date markers |
| `charts/WorkflowStateRow.tsx` | Horizontal stacked priority bars with inline counts across open stages and closed terminal stages (`Done`) |
| `TopBar.tsx` | Sticky frosted navbar: logo, center `ScopeBar`, ambient Sync Status / Refresh button, `Charts` toggle, theme toggle, Admin Ops trigger |
| `ScopeBar.tsx` | Unified tokenized fuzzy scope picker (`Context`, `Milestone`, and `Team` when `> 1`, supporting multi-term combined quick-apply like `proj v14`) beside inline `30d`/`90d`/`1y`/`All` presets and a custom date popover |
| `SummaryBar.tsx` | Quick-filter pill groups rendered automatically in `IssuePanel` when `Charts` is toggled OFF |
| `IssueSearchInput.tsx` | Expanding inline search pill (`Ctrl/Cmd+K` focus, `Escape` blur, clear button) |
| `IssueTable.tsx` | `@tanstack/react-table` grid with sticky header, sortable columns, default hierarchy indentation, colored label pills, conditional `Stage` and `Quality hints` columns |
| `IssueBoard.tsx` | Kanban board with horizontally scroll-synced sticky lane headers, priority mix bars, clickable lane priority pills, and issue cards |
| `IssuePanel.tsx` | Unified toolbar with named filter chips (`Clear all`), optional `SummaryBar` strip when charts are hidden, `Fit`/10/20/30 paging (`ResizeObserver`), Table/Board switch |
| `OverviewWorkspace.tsx` | Single-viewport responsive hybrid workspace: persistent slim Release Rail + `380 px` left analytics rail (`>= 1360px` Table with Charts ON) or 4-card top bento strip (`< 1360px` or Board) beside/above `IssuePanel` |
| `AdminModal.tsx` | Password prompt and controls for Collector (L1), Processor (L2), Cache Clear, and execution logs |
| `App.tsx` | Top-level data loader, URL synchronization (`replaceState` / `popstate`), theme persistence, and `Charts` toggle state |

## 4. URL Query Parameters, Shortcuts, and Environment Variables

### 4.1 URL Query Parameters

| Parameter | Values | Default / Omitted Behavior |
|---|---|---|
| `view` | `compact` (Charts OFF), `analytics` (alias for ON) | Omitted when Charts ON (default) |
| `summary` | Summary pill ID (e.g., `open`, `priority_P1`) | Omitted when none |
| `f_stage` | Stage name | Omitted |
| `f_state` | `opened`, `closed`, `all` | Omitted (defaults to `opened` in filtering) |
| `f_priority` | Priority label or `Unset` | Omitted |
| `f_issue_type` | Issue type label or `Unset` | Omitted |
| `f_signal` | `MISSING_MILESTONE`, `UNASSIGNED_OWNER`, `MIXED_CLASSIFICATION` | Omitted |
| `f_recent` | `created`, `closed` | Omitted |
| `f_day` | `YYYY-MM-DD` (requires valid `f_day_kind`) | Omitted |
| `f_day_kind` | `created`, `closed` | Omitted |
| `f_query` | Search text | Omitted |
| `g_team` | Team / Domain name | Omitted (`All`) |
| `g_context` | Context / Sub-project name | Omitted (`All`) |
| `g_milestone` | Milestone title | Omitted (`All`) |
| `g_preset` | `30d`, `90d`, `1y`, `custom` | Omitted (`all`) |
| `g_start` | `YYYY-MM-DD` (when `g_preset=custom`) | Omitted |
| `g_end` | `YYYY-MM-DD` (when `g_preset=custom`) | Omitted |

### 4.2 Keyboard Shortcuts
- `Ctrl+K` (or `Cmd+K` on macOS): focus and select the inline issue search box.
- `Escape`: blur search input, close open `ScopeBar` popovers, close the unscheduled milestones popover (focus returns to the release rail tray), or close `AdminModal`.

### 4.3 Server Environment Variables
- `HOST`: bind address for `python -m app.dashboard` (default `127.0.0.1`).
- `PORT`: bind port for `python -m app.dashboard` (default `8501`).
- `ADMIN_PASSWORD`: admin password checked by `/api/admin/login` (default `admin`).

## 5. Removed Artifacts and Updated Operational Files

- **Removed Python packages:** `streamlit`, `plotly`, `streamlit-elements`, `streamlit-keyup`.
- **Added Python packages:** `fastapi`, `uvicorn[standard]`.
- **Removed directories/files:** `.streamlit/`, `data/config/layouts/`, all legacy Streamlit files under `app/dashboard/` (`main.py`, `engine.py`, `registry.py`, `sidebar.py`, `components.py`, `figure_cache.py`, `theme.py`, `views/*`, `widgets/*`), `docs/spec/TSD_Layer3_PresentationLayer_Modularization.md`, and 15 Streamlit-specific test files in `tests/`.
- **Updated build/deploy files:** `pyproject.toml`, `uv.lock`, `.gitignore`, `Dockerfile` (two-stage Node 22 + Python 3.11), `scripts/docker-entrypoint.sh`, `setup.sh`.
- **New/updated test suites:**
  - `tests/test_dashboard_service.py` and `tests/test_dashboard_api.py` (alongside updated `tests/test_validator.py` and `tests/test_local_data_tools.py`).
  - `frontend/src/lib/__tests__/{facets,search,timeline,board}.test.ts`.
