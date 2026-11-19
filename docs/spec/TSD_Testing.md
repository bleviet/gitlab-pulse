# Technical Specification: Testing & Validation

**Status:** Current implementation reference  
**Scope:** Existing automated tests and supported local validation workflows.

## 1. Automated Test Suite

The repository ships a Python `pytest` suite (`tests/`) and a frontend `Vitest` suite (`frontend/src/lib/__tests__/`):

- Backend (`uv run pytest`: 41 tests):
  - FastAPI dashboard endpoints, auth/admin routes, and `DashboardService` mtime caching
  - Processor validation and enrichment behavior
  - Collector orchestration edge cases
  - Hierarchy sorting
  - Local synthetic data tools and setup/config safety checks
- Frontend (`cd frontend && npm test`: 6 test files, 23 tests):
  - `analytics.test.ts`, `board.test.ts`, `facets.test.ts`, `scopeSearch.test.ts`, `search.test.ts`, `timeline.test.ts`
  - Plus TypeScript strict check (`npm run typecheck`) and production bundle build (`npm run build`)

Current commands:

```bash
uv run pytest tests/ -v
cd frontend && npm run typecheck && npm test && npm run build
```

## 2. Covered Surfaces

### 2.1 Collector

Tests verify:

- missing remote projects fail normally when no local fallback exists
- missing remote projects are skipped when matching local seeded parquet data exists

### 2.2 Processor and validation

Tests verify:

- metric enrichment
- classification behavior
- validation failures for missing or conflicting labels
- distinct issue counting in quality summaries

### 2.3 Dashboard & Frontend Domain Logic

Tests verify:

- `/api/health`, `/api/dashboard`, and `/api/admin/*` endpoints and session auth
- `DashboardService` context collapsing, YAML palette resolution, and file-mtime cache invalidation
- issue hierarchy indentation, lane ordering, and priority ranking
- unified fuzzy scope search (`proj v14`), `Ctrl/Cmd+K` fuzzy issue search, URL query serialization (`f_*` / `g_*` / `view`), workflow state closed buckets, and milestone rail status calculations

### 2.4 Local demo tooling

Tests verify:

- seeder assignment-rate and team-size behavior
- seeded milestones without a due date (open and all-closed) with at most one due date per milestone title
- local issue URL generation
- local project discovery and deletion utilities
- overview quality-signal helpers

## 3. Supported Manual Validation Workflows

### 3.1 Synthetic local dataset

```bash
uv run python tools/seeder.py --count 1000 --inject-errors
uv run python app/processor/main.py
cd frontend && npm run build && cd ..
uv run python -m app.dashboard
```

### 3.2 Local data manager

```bash
uv run python tools/local_data_manager.py
```

### 3.3 Live GitLab pipeline

```bash
uv run python app/collector/orchestrator.py
uv run python app/processor/main.py
```

## 4. Notes on Scope

- This document describes the test surface that actually exists in the repository today
- There is currently no checked-in `tools/gitlab_seeder.py`
- Performance goals remain useful as operational guidance, but they are not enforced by the automated test suite at this time
