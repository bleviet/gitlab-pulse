# How-to Guides: Developing, Extending, and Running Layer 3

Task-focused recipes for working with the FastAPI + React/TypeScript dashboard.

## Run the Built Dashboard Locally

1. Ensure `frontend/dist/` has been built:
   ```bash
   cd frontend && npm ci && npm run build && cd ..
   ```
2. Start the FastAPI server (defaults to `127.0.0.1:8501`):
   ```bash
   uv run python -m app.dashboard
   ```
   Optional flags:
   ```bash
   uv run python -m app.dashboard --host 0.0.0.0 --port 8501
   ```

## Run the Hot-Reload Development Loop

Use two terminals so API and UI changes reload independently:

1. Terminal 1 — FastAPI with auto-reload on `:8501`:
   ```bash
   uv run python -m app.dashboard --reload
   ```
2. Terminal 2 — Vite dev server on `:5173` (proxies `/api/*` to `:8501`):
   ```bash
   cd frontend && npm run dev
   ```
3. Open `http://127.0.0.1:5173`. Rebuild `frontend/dist/` with `npm run build` before serving directly from `:8501`.

## Run All Tests, Linters, and Type Checks

Backend (from repository root):
```bash
uv run pytest
uv run ruff check app/dashboard/ tests/test_dashboard_api.py tests/test_dashboard_service.py tests/test_local_data_tools.py tests/test_validator.py
uv run mypy app/dashboard/
```

Frontend (from `frontend/`):
```bash
npm run typecheck
npm test
npm run build
```

## Expose a New Parquet Column in the API and UI

1. Verify Layer 2 emits the column in `data/analytics/issues_valid.parquet`.
2. Add the typed field to `IssueItem` in `app/dashboard/schemas.py`.
3. Extract and pass the column in `DashboardService._build_payload()` inside `app/dashboard/service.py` using `_col_list(unique_df, "<column_name>")`.
4. Add the matching property to `IssueItem` in `frontend/src/lib/types.ts`.
5. Render or sort on the field in `frontend/src/components/IssueTable.tsx` or `IssueBoard.tsx`.
6. Add coverage in `tests/test_dashboard_service.py` and rebuild `frontend/dist/`.

## Add a New Filter Facet and URL Parameter

1. Add the field to `IssueFacets` in `frontend/src/lib/types.ts`.
2. Register the key in `FACET_KEYS`, validate it inside `cleanFacets()`, apply the filter predicate in `applyFacets()`, and emit a chip label in `buildFacetChips()` inside `frontend/src/lib/facets.ts`.
3. Trigger updates via `onChangeFacets` (in `IssuePanel.tsx`) or `onSetChartFilter` (in `OverviewWorkspace.tsx`).
4. Add unit tests in `frontend/src/lib/__tests__/facets.test.ts` verifying filtering, URL serialization (`f_<key>`), and malformed-value rejection.

## Override Semantic Data Colors via YAML Rules

The Settings screen has a **Colours** section that does the same without editing a file (default rule set only). By hand:

1. Edit or create a team YAML file in the active rules directory: `data/rules/` once it contains rule files (after the first save from the Settings screen), otherwise `app/config/rules/` (see `app/config/rules/default.yaml` for the schema).
2. Add hex overrides under `colors.light` and `colors.dark` for keys such as `p1`, `p2`, `p3`, `bug`, `feature`, `ms_on_track`, or `ms_overdue`.
3. Reload the dashboard (or click `Clear Cache & Reload` in Admin Operations); `DashboardService` detects the YAML `st_mtime_ns` change automatically.

## Run Pipeline Steps via Admin Operations

1. Click **Ops** (or **Admin**) in the top-right navigation bar.
2. Enter `ADMIN_PASSWORD` (default `admin`).
3. Click **Run Collector (L1)** or **Run Processor (L2)**. On exit code `0`, the backend clears the `DashboardService` cache and the SPA reloads `/api/dashboard` automatically.

## Build and Run With Docker

```bash
cp .env.example .env
docker compose up --build
```

The multi-stage `Dockerfile` builds `frontend/dist/` in `node:22-slim`, copies it into the `python:3.11-slim` runtime image, seeds synthetic data when `SEED_LOCAL_DATA=true` and `data/processed/` is empty, and starts Uvicorn on port `8501`.
