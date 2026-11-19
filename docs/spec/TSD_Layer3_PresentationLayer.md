# Technical Specification: Layer 3 - Presentation Layer (FastAPI + React/TypeScript)

**Version:** 3.0  
**Status:** Implemented

## 1. Overview

Layer 3 provides a fast, client-reactive presentation architecture split into two cleanly bounded parts:

- **Backend API (`app/dashboard/`)**: A thin FastAPI server that reads Layer 2 Parquet datasets, collapses context rows, resolves YAML theme palettes and stage metadata, and exposes compressed JSON endpoints plus static SPA serving.
- **Frontend SPA (`frontend/`)**: A React + TypeScript application bundled with Vite that performs filtering, fuzzy search, chart aggregation, table/board paging, and SVG chart rendering directly in browser memory.

The legacy Streamlit UI, Plotly wrapper layer, and experimental Custom View builder have been removed.

## 2. Backend Architecture (`app/dashboard/`)

| Module | Responsibility |
|---|---|
| `schemas.py` | Frozen Pydantic v2 DTOs (`IssueItem`, `DashboardPayload`, `AdminJobResponse`, etc.) |
| `data_loader.py` | Parquet readers (`issues_valid.parquet`, `labels_*.parquet`) and `sync_state.json` loader |
| `utils.py` | Assignee/label normalization, quality signals and hints, hierarchy DFS sort |
| `palettes.py` | Theme-aware light/dark semantic color maps merged with YAML rule overrides |
| `service.py` | `DashboardService` with mtime-keyed payload caching and thread-safe invalidation |
| `admin.py` | Cookie-authenticated `/api/admin/*` endpoints running Layer 1/2 pipeline scripts |
| `server.py` | FastAPI app factory with GZip compression, CORS for Vite dev, and SPA fallback serving |
| `__main__.py` | Uvicorn CLI entry point (`uv run python -m app.dashboard`, default port `8501`) |

### 2.1 HTTP API Surface

- `GET /api/health` -> `{"status": "ok"}`
- `GET /api/dashboard` -> `DashboardPayload` (issues with collapsed `contexts`, `filter_options`, `label_styles`, `stages`, `palettes`, `sync_status`, `version`, `generated_at`)
- `GET /api/admin/status` -> `{"authenticated": bool}`
- `POST /api/admin/login` -> verifies `ADMIN_PASSWORD` and sets an `HttpOnly`, `SameSite=lax` cookie (`pulse_admin_session`)
- `POST /api/admin/logout` -> revokes session token and clears cookie
- `POST /api/admin/run/collector` -> executes `app/collector/orchestrator.py` and invalidates payload cache on success
- `POST /api/admin/run/processor` -> executes `app/processor/main.py` and invalidates payload cache on success
- `POST /api/admin/clear-cache` -> clears the cached payload

## 3. Frontend Architecture (`frontend/src/`)

| Area | Modules |
|---|---|
| `styles/` | Self-hosted fonts (`fonts.css`), bahonavi dark/light CSS variables (`tokens.css`), layout and component styles (`global.css`) |
| `lib/` | Pure TypeScript domain logic (`types.ts`, `colors.ts`, `search.ts`, `scopeSearch.ts`, `facets.ts`, `summary.ts`, `timeline.ts`, `board.ts`, `analytics.ts`, `api.ts`) |
| `components/charts/` | Responsive SVG charts (`ReleaseTimeline`, `PriorityDonut`, `QualitySignalsChart`, `UnscheduledMilestonesChart`, `DailyVelocityChart`, `WorkflowStateRow`) |
| `components/` | `TopBar`, `ScopeBar`, `OverviewWorkspace`, `SummaryBar`, `IssueSearchInput`, `IssuePanel`, `IssueTable`, `IssueBoard`, `AdminModal` |

### 3.1 Rationale for Client-Side Filtering & SVG Charts

Because GitLab Pulse typically operates on thousands of issues per workspace, shipping the collapsed issue payload once (~100 KB gzipped) lets every summary pill click, chart slice selection, search keystroke, column sort, and page switch complete in a few milliseconds on the client without network round-trips or server re-execution.
