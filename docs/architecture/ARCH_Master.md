# Master Architecture: GitLabInsight

Version: 1.1  
Status: Current implementation reference  
Scope: End-to-end data flow from GitLab ingestion through local analytics, dashboard rendering, and AI assistance.

## 1. Executive Summary

**GitLabInsight** is a local-first analytics platform for GitLab issue data. It ingests issues from GitLab or synthetic local seed data, normalizes them into Parquet, enriches them with rules-based workflow and quality metadata, and renders them in a Streamlit dashboard with optional local Ollama-backed AI assistance.

The architecture follows a layered data pipeline:

| Layer | Name | Path | Purpose |
| :---- | :---- | :---- | :---- |
| **Layer 0** | Raw | `data/raw/` | Audit copy of GitLab API issue payloads |
| **Layer 1** | Processed | `data/processed/` | Standardized technical mirror (`issues_*`, `milestones_*`, `labels_*`) |
| **Layer 2** | Analytics | `data/analytics/` | Enriched analytics dataset and quality hints |
| **Layer 4** | AI Memory | `data/ai/` | Persistent summaries and chat history per issue |

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
5. Upsert issues into `data/processed/issues_{project_id}.parquet`.
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

**Role:** Render analytics through Streamlit using a curated overview and a customizable layout builder.

### 4.1 Current pages

The active page set in `app/dashboard/main.py` is:

- **Overview**
- **Custom**
- **Admin** (only when authenticated as admin)

There is a `views/hygiene.py` file in the repository, but it is not part of the active top-level navigation.

### 4.2 Dashboard builder status

The dashboard builder is implemented as a **hybrid layout engine**:

- **Edit mode:** uses `streamlit-elements` for drag-and-drop and resize interactions
- **View mode:** renders with native Streamlit columns based on persisted grid coordinates

Layouts are stored as JSON files under `data/config/layouts/`.

### 4.3 Overview status

The Overview page is the main curated workflow view. It currently includes:

- open issues by priority
- closed issues by priority
- daily new vs. closed issues
- issues by workflow state
- milestone release timeline
- open vs. closed issues
- issue quality signals
- issue drill-down table with fuzzy search and AI status markers
- issue details dialog and AI assistant integration

### 4.4 Caching

The dashboard uses `@st.cache_data` with short TTLs for analytics loading, including a 2-minute TTL on the main data loaders.

## 5. Layer 4: AI Services

**Role:** Provide local, persistent issue summarization and follow-up chat.

### 5.1 Implemented components

- `app/ai/models.py`
- `app/ai/service.py`
- dashboard integration in `app/dashboard/widgets/features/ai_assistant.py`
- sidebar AI endpoint configuration in `app/dashboard/sidebar.py`

### 5.2 Implemented behavior

- health-check the configured Ollama endpoint
- list available models from Ollama
- generate a structured summary for a selected issue
- persist summary and chat history in `data/ai/chat_{issue_id}.parquet`
- mark summaries as stale when `issue.updated_at > ref_issue_updated_at`

## 6. Local Data Tooling

The repository supports a fully local demo and validation workflow:

- `tools/seeder.py` creates synthetic Layer 1 issue data directly
- `tools/local_data_manager.py` can inspect, seed, delete, process, and reset local synthetic projects

This allows dashboard and processor testing without a live GitLab connection.

## 7. Operational Notes

- The app is designed for internal or local use, not direct public internet exposure.
- Admin actions are password-gated in the Streamlit UI, but broader production auth should still be handled externally.
- The architecture is intentionally local-first: persistent files in `data/` are part of normal operation, not just temporary artifacts.
