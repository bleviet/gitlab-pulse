# Technical Specification: Layer 2 - Domain Logic & Validation

**Status:** Implemented  
**Scope:** Current processor behavior for enrichment, context mapping, and quality output.

## 1. Configuration Engine

### 1.1 Rule loading

`app/processor/rule_loader.py` loads YAML rules from `app/config/rules/` and resolves the correct rule set for each project. The default rule acts as the global fallback.

## 2. Enrichment Pipeline

`app/processor/main.py` currently applies the following steps per project:

1. Load `data/processed/issues_{project_id}.parquet`
2. Enrich metrics
3. Apply classification mappings
4. Assign workflow stage and stage type
5. Explode matching contexts into multiple logical rows
6. Validate issues against configured rules
7. Merge orphan-context handling into both analytics and quality outputs

## 3. Implemented Behaviors

### 3.1 Vectorized metrics

Metrics are calculated with Pandas operations rather than row-by-row loops. This includes age-style and cycle-time style metrics used by the dashboard.

### 3.2 Context explosion

If a single issue matches multiple configured contexts, Layer 2 emits one logical analytics row per matched context. This keeps Layer 3 filtering simple and explicit.

### 3.3 Orphan context handling

Issues that do not match any configured context are not dropped. Instead:

- they remain in `issues_valid.parquet` with empty context fields
- they also produce `MISSING_CONTEXT` rows in `data_quality.parquet`

This preserves reporting completeness while still surfacing the data quality problem.

### 3.4 Quality output lifecycle

`data_quality.parquet` is always rewritten, even when there are zero current quality hints. This clears stale quality output from earlier runs.

## 4. Data Outputs

| File | Content |
| :---- | :---- |
| `data/analytics/issues_valid.parquet` | Enriched analytics dataset |
| `data/analytics/data_quality.parquet` | Validation and quality hints |

## 5. Rationale

- **Modular YAML rules:** different teams can tailor interpretation without changing processor code
- **Split analytics vs. quality output:** analytics stays usable while quality issues remain actionable
- **Context explosion in Layer 2:** avoids repeated label parsing in the UI layer
