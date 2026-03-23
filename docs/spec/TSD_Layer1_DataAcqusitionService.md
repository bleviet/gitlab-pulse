# Technical Specification: Layer 1 - Data Acquisition Service

**Status:** Implemented  
**Scope:** Current collector behavior for GitLab ingestion and Layer 1 persistence.

## 1. Components

### 1.1 Ingestion Orchestrator

`app/collector/orchestrator.py` coordinates the collection pipeline:

1. Resolve project IDs from CLI, environment, or tracked sync state
2. Fetch issues incrementally unless `--full-sync` is set
3. Persist raw issue payloads to Layer 0
4. Enrich issues with GraphQL hierarchy data when possible
5. Upsert Layer 1 issue parquet files
6. Persist milestone and label parquet side datasets
7. Update sync state

### 1.2 API Clients

- **REST client:** fetches issues, milestones, labels, and project path metadata
- **GraphQL client:** fetches work-item hierarchy using the project's full path

## 2. Sync Algorithm

1. **Check State:** read `data/state/sync_state.json`
2. **Fetch Issues:** call REST with `updated_after` unless running full sync
3. **Persist Raw:** save raw issue payloads to `data/raw/`
4. **Fetch Side Data:** fetch milestones and labels independently
5. **Enrich Hierarchy:** fetch parent/child work-item data through GraphQL when project path resolution succeeds
6. **Persist Layer 1:** upsert `data/processed/issues_{project_id}.parquet`
7. **Update State:** store latest seen `updated_at` and issue counts

## 3. Layer 1 Outputs

| File | Behavior |
| :---- | :---- |
| `issues_{project_id}.parquet` | Upserted by issue `id` |
| `milestones_{project_id}.parquet` | Full replace on each sync |
| `labels_{project_id}.parquet` | Full replace on each sync |

Writes are performed atomically through temporary files before rename.

## 4. Current Edge Cases

### 4.1 Incremental project discovery

If `PROJECT_IDS` is omitted, the collector falls back to previously tracked projects from sync state. This enables repeat syncs and admin-triggered syncs after the initial setup.

### 4.2 Local seeded project preservation

If GitLab returns `404` for a project but `data/processed/issues_{project_id}.parquet` already exists, the orchestrator marks that project as skipped local data instead of failing the overall run.

### 4.3 Hierarchy enrichment fallback

GraphQL hierarchy enrichment is best-effort. If project path lookup fails, issue sync still proceeds using REST data only.

## 5. Rationale

- **Parquet with Snappy:** fast columnar reads for downstream analytics
- **Pydantic-backed schema normalization:** predictable typing at the ingestion boundary
- **Incremental sync state:** reduces repeated GitLab API load during normal operation
