# Master Architecture: GitLab Pulse

Version: 1.1  
Status: Current implementation reference  
Scope: End-to-end data flow from GitLab ingestion through local analytics and dashboard rendering.

## 1. Executive Summary

**GitLab Pulse** is a local-first analytics platform for GitLab issue data. It ingests issues from GitLab or synthetic local seed data, normalizes them into Parquet, enriches them with rules-based workflow and quality metadata, and serves them through a FastAPI API to a React/TypeScript single-page dashboard.

The architecture follows a layered data pipeline:

| Layer | Name | Path | Purpose |
| :---- | :---- | :---- | :---- |
| **Layer 0** | Raw | `data/raw/` | Audit copy of GitLab API issue payloads |
| **Layer 1** | Processed | `data/processed/` | Standardized technical mirror (`issues_*`, `milestones_*`, `labels_*`) |
| **Layer 2** | Analytics | `data/analytics/` | Enriched analytics dataset and quality hints |

## 2. Layer 1: Data Acquisition

**Role:** Fetch issue data from GitLab and persist a clean technical mirror for downstream processing.

### 2.1 Implemented components

- `app/collector/orchestrator.py`: orchestration and CLI entry point
- `app/collector/rest_client.py`: issue, milestone, and label retrieval
- `app/collector/gql_client.py`: work-item hierarchy enrichment
- `app/collector/state.py`: incremental sync state management

### 2.2 Implemented behavior

1. Read project IDs from `--project-ids`, `PROJECT_IDS`, or previously tracked state.
2. Fetch changed issues incrementally using `updated_after` unless `--full-sync` is used.
3. Persist raw issue payloads into Layer 0.
4. Fetch hierarchy data through GraphQL when a project path is available.
5. Upsert issues into `data/processed/issues_{project_id}.parquet` on incremental sync; replace the file on full sync (the only way to drop issues deleted in GitLab).
6. Persist milestones and labels separately as full-refresh side datasets.
7. Update `data/state/sync_state.json`.

### 2.3 Notable operational edge case

If a project returns `404` but a matching `data/processed/issues_{project_id}.parquet` already exists, the collector treats that project as **local seeded data** and skips it instead of failing the full run. This preserves synthetic local demo data when those IDs remain in `PROJECT_IDS`.

## 3. Layer 2: Domain Logic and Validation

**Role:** Transform the Layer 1 mirror into analytics-ready issue data plus actionable quality hints.

### 3.1 Implemented components

- `app/processor/main.py`
- `app/processor/enricher.py`
- `app/processor/validator.py`
- `app/processor/rule_loader.py`

### 3.2 Implemented behavior

- Load all `issues_*.parquet` files from Layer 1
- Apply vectorized metrics enrichment
- Map classifications and workflow stages from YAML rules
- Perform **context explosion** so a single issue can appear in multiple logical contexts
- Validate issues against rule-driven quality expectations
- Write:
  - `data/analytics/issues_valid.parquet`
  - `data/analytics/data_quality.parquet`

### 3.3 Current quality model

Issues without matching contexts are handled in two ways:

- they remain in the main analytics dataset so reporting stays complete
- they also produce `MISSING_CONTEXT` quality hints so the assignment gap is visible

## 4. Layer 3: Presentation

**Role:** Serve Layer 2 analytics data via FastAPI (`app/dashboard/`) and render interactive views in a React/TypeScript SPA (`frontend/`).

### 4.1 Architecture rationale

We replaced Streamlit with a thin FastAPI backend and a React/TypeScript SPA so that filtering, fuzzy search, cross-chart selection, table/board paging, and sticky headers execute synchronously in browser memory without full-script reruns, iframe bridges, or polling intervals.

### 4.2 Active views

- **Overview workspace (`OverviewWorkspace`)**: single-viewport (`100vh`) workspace with a persistent Release Timeline rail, a `Charts` toggle (default ON; `?view=compact` when hidden), interactive SVG analytics cards (or `SummaryBar` quick-filter pills when charts are hidden), named filter chips, inline `Ctrl/Cmd+K` search, and the issue table/board.
- **Admin Operations modal**: password-gated cookie session for triggering the Layer 1 collector, Layer 2 processor, and server cache invalidation.

The legacy experimental Custom View layout builder has been removed.

### 4.3 Caching

`DashboardService` caches the prepared `DashboardPayload` in memory keyed on the modification timestamps (`st_mtime_ns`) of `issues_valid.parquet`, `labels_*.parquet`, `sync_state.json`, and the active rule files, and supports explicit invalidation after admin runs.

### 4.4 Rule editing

Rules are edited in the dashboard Settings screen instead of by hand. We added the editor because the people who decide how labels map to types and workflow stages (managers, team leads) are usually not the people who can edit a YAML file and run the processor from a terminal, and because a hand-edited file fails silently: a syntax error skips the file and an invalid pattern never matches.

- **YAML stays the storage format.** New teams are still new rule files (architecture rule "extend, don't modify"), and the processor is unchanged. The editor is a second way to produce the same files.
- **User rules live in `data/rules/`; `app/config/rules/` is a template.** Rules saved from the UI must survive a Docker image rebuild and must not leave a git checkout modified. The template is used until the first save, which copies it.
- **Viewing is open, saving needs the admin session.** Rules contain no secrets, and letting everyone read them explains why the dashboard shows what it shows. Changing them alters every chart, so it uses the existing admin password rather than a second role system.
- **Saving applies.** A save validates, writes atomically, keeps the replaced file in `data/rules/.history/`, runs the processor, and invalidates the payload cache, so the user never has to know that a separate processing step exists.
- **Consequences are shown before saving.** The Settings screen asks the backend for a dry run of the draft shortly after each change and shows issue counts before and after, labels that no rule uses, and entries that match no issue. Someone who does not know the rule format cannot predict what an edit does; the numbers come from the same pipeline code as a real processor run, so what is previewed is what a save produces.
- **One rule set per team, one default.** A rule set lists its projects; the rule set with no project list covers everything else and cannot be deleted. This keeps the existing file-per-team model and gives every project exactly one answer to "which rules apply to me".
- **Recent saves can be undone from the screen.** The 20 most recent earlier versions of each rule set are kept. They are loaded back into the editor as unsaved changes instead of being restored directly, so the user sees the effect first and the change goes through the same validation and processing as any other.
- **Suggestions are computed in the browser from the payload.** "Suggest from my labels" reads GitLab's scoped label form (`scope::value`) from the labels already loaded and proposes rows; it only fills the unsaved draft, so the proposal goes through the same preview and save as a manual edit.
- **Label choices come from the data.** The editor offers the labels already present in the dashboard payload (`label_styles`, `issues[].labels`) instead of asking the user to type label names from memory.

## 5. Local Data Tooling

The repository supports a fully local demo and validation workflow:

- `tools/seeder.py` creates synthetic Layer 1 issue data directly
- `tools/local_data_manager.py` can inspect, seed, delete, process, and reset local synthetic projects

This allows dashboard and processor testing without a live GitLab connection.

## 6. Operational Notes

- The app is designed for internal or local use, not direct public internet exposure.
- Admin actions are password-gated via `HttpOnly` session cookies (`ADMIN_PASSWORD`), but broader production auth should still be handled externally.
- The architecture is intentionally local-first: persistent files in `data/` are part of normal operation, not just temporary artifacts.

## 7. Static Demo on GitHub Pages

The public demo at `https://bleviet.github.io/gitlab-pulse/demo/` is the same SPA built with `vite build --mode demo`, reading a static JSON snapshot (`demo-data/dashboard.json`) instead of `GET /api/dashboard`. We chose a snapshot because the SPA already does all filtering and charting client-side from one payload, so a static host is enough: there is no server to run or pay for and no admin endpoint exposed. `tools/export_demo_payload.py` writes the snapshot from `DashboardService` after the workflow (`.github/workflows/pages.yml`) seeds and processes synthetic data. The workflow also runs weekly because the seeded dates are relative to the day it runs, so the demo would otherwise age. Jekyll stays as the builder for `docs/` so the existing homepage and documentation behave as before; the demo build is copied into `docs/demo/` before Jekyll runs. Deployment uses `actions/deploy-pages`, so the repository's Pages source must be set to "GitHub Actions" (Settings, Pages); with the legacy "Deploy from a branch" source the demo is never published, because `docs/demo/` is gitignored.
