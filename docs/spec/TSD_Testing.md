# Technical Specification: Testing & Validation

**Status:** Current implementation reference  
**Scope:** Existing automated tests and supported local validation workflows.

## 1. Automated Test Suite

The repository currently ships a focused pytest suite covering:

- dashboard grid engine behavior
- processor validation and enrichment behavior
- collector orchestration edge cases
- local synthetic data tools
- setup/config safety checks

Current command:

```bash
uv run pytest tests/ -v
```

At the time of this update, the suite contains **39 passing tests**.

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

### 2.3 Dashboard behavior

Tests verify:

- Streamlit grid width calculation
- layout row grouping and ordering
- overview/local-data helper functions used by the dashboard

### 2.4 Local demo tooling

Tests verify:

- seeder assignment-rate and team-size behavior
- local issue URL generation
- local issue detail resolution
- local project discovery and deletion utilities
- overview quality-signal helpers

## 3. Supported Manual Validation Workflows

### 3.1 Synthetic local dataset

```bash
uv run python tools/seeder.py --count 1000 --inject-errors
uv run python app/processor/main.py
uv run streamlit run app/dashboard/main.py
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
