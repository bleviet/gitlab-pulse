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
| `admin.py` | Cookie-authenticated `/api/admin/*` endpoints running Layer 1/2 pipeline scripts; `AdminSessions` token store shared with the rules router |
| `rules_api.py` | Rule editor endpoints: converts between `DomainRule` and the list-based API model, validates, saves through `RuleStore`, and re-runs the processor |
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
- `GET /api/rules` -> `RuleSetsResponse` (every rule set with its `revision`, files that failed to load, and whether the rules come from the `template` or the `user` directory). No authentication; rules contain no secrets.
- `PUT /api/admin/rules/{name}` -> validates and saves one existing rule set, runs `app/processor/main.py`, and invalidates the payload cache. `401` without an admin session, `404` for an unknown rule set, `409` when the submitted `revision` is stale, `422` with `{"message", "problems": [{"path", "message"}]}` when validation fails. A `200` response carries the saved rule set and the processor job result; `job.success` is `false` when the rules were saved but processing failed.

The rule API represents `classification` as ordered lists (`[{name, values: [{name, labels, title}]}]`) rather than the nested mapping used in YAML. Order decides which value wins and how priorities rank, and JavaScript re-orders object keys that look like integers (a priority named `1`), so a mapping cannot carry the order to the browser reliably.

Two checks live in `rules_api.py` rather than in `validate_rule_set()`. Duplicate classification category or value names are detected on the list form before conversion, because the mapping would silently collapse them. Project conflicts between rule sets are reported only when the submitted `project_ids` differ from the stored ones, so a conflict that already exists in hand-written files does not block edits to other fields.

Pipeline runs triggered through the admin endpoints and through a rule save are serialised with one lock so two processor runs cannot write the analytics files at the same time.

## 3. Frontend Architecture (`frontend/src/`)

| Area | Modules |
|---|---|
| `styles/` | Self-hosted fonts (`fonts.css`), bahonavi dark/light CSS variables (`tokens.css`), layout and component styles (`global.css`) |
| `lib/` | Pure TypeScript domain logic (`types.ts`, `colors.ts`, `search.ts`, `scopeSearch.ts`, `facets.ts`, `summary.ts`, `timeline.ts`, `board.ts`, `analytics.ts`, `api.ts`), plus the rule editor helpers `rulePatterns.ts` (pattern prefix parsing), `labelInventory.ts` (labels and usage counts from the payload), `ruleDraft.ts` (draft list helpers and client-side validation) |
| `components/charts/` | Responsive SVG charts (`ReleaseTimeline`, `PriorityDonut`, `QualitySignalsChart`, `UnscheduledMilestonesChart`, `DailyVelocityChart`, `WorkflowStateRow`) |
| `components/` | `TopBar`, `ScopeBar`, `OverviewWorkspace`, `SummaryBar`, `IssueSearchInput`, `IssuePanel`, `IssueTable`, `IssueBoard`, `AdminModal` |
| `components/settings/` | `SettingsWorkspace` (rule editor dialog, load/save flow), `MatcherInput` (label picker and pattern chips), `ClassificationEditor`, `StagesEditor`, `ContextsEditor`, `QualityEditor`, and small shared controls |

### 3.1 Rationale for Client-Side Filtering & SVG Charts

Because GitLab Pulse typically operates on thousands of issues per workspace, shipping the collapsed issue payload once (~100 KB gzipped) lets every summary pill click, chart slice selection, search keystroke, column sort, and page switch complete in a few milliseconds on the client without network round-trips or server re-execution.

### 3.2 Demo mode

`npm run build:demo` runs Vite with `--mode demo`, `--base /gitlab-pulse/demo/` and `--outDir dist-demo`. `IS_DEMO` (`frontend/src/lib/api.ts`, `import.meta.env.MODE === "demo"`) changes the following:

- `fetchDashboard()` reads `${import.meta.env.BASE_URL}demo-data/dashboard.json` instead of `/api/dashboard`.
- `App` does not call `fetchAdminStatus` and does not render `AdminModal` or `SettingsWorkspace`.
- `TopBar` hides the refresh/sync button, the Settings button, and the Ops/admin button and shows a "Demo · synthetic data" chip linking to the README quick start.
- Public assets use the Vite base: the logo path uses `BASE_URL`, and Vite rewrites the favicon links in `index.html` and the font URLs in `fonts.css`.

The normal build (base `/`) is unaffected. The snapshot is produced by `tools/export_demo_payload.py`.
