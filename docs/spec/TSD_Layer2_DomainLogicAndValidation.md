# Technical Specification: Layer 2 - Domain Logic & Validation

**Status:** Implemented  
**Scope:** Current processor behavior for enrichment, context mapping, and quality output.

## 1. Configuration Engine

### 1.1 Rule loading

`app/processor/rule_loader.py` loads YAML rules and resolves the correct rule set for each project. The default rule (the file with an empty `project_ids` list) acts as the global fallback. Files are read in sorted order, and files that fail to load are skipped and recorded in `RuleLoader.load_errors`.

`resolve_rules_path()` picks the directory: `data/rules/` when it contains at least one `*.yaml` file, otherwise the shipped template directory `app/config/rules/`. The processor CLI, `DashboardService`, and `tools/local_data_manager.py` use it unless a path is passed explicitly.

### 1.2 Rule store

`app/processor/rule_store.py` is the write side used by the dashboard Settings screen:

- `RuleStore.list_rule_sets()` returns every rule file of the active directory with a revision (SHA-256 of the file content).
- `RuleStore.write()` rejects names that are not a plain file stem, rejects a stale revision, seeds `data/rules/` from the template directory on the first write, copies the replaced file to `data/rules/.history/` (newest 20 kept per file), and writes atomically (`*.tmp` then `os.replace`). Seeding is atomic per file, not as a set: if the process is interrupted between two template files, `data/rules/` becomes active with only part of the template, and the missing files have to be copied by hand.
- `dump_rule()` serialises a `DomainRule` without the deprecated keys (`label_mappings`, `title_patterns`, `contexts.method`, `contexts.patterns`) and without sorting keys, because the key order of `classification` decides which value wins and how priorities rank.
- `validate_rule_set()` returns plain-language problems with a field path for conditions the lenient `DomainRule` model accepts: empty names, duplicate stage or context names, unknown stage types, empty patterns, regular expressions that do not compile, thresholds below 1, a project claimed by two rule sets, and more than one default rule set.

## 2. Enrichment Pipeline

`app/processor/main.py` currently applies the following steps per project:

1. Load `data/processed/issues_{project_id}.parquet`
2. Enrich metrics
3. Apply classification mappings
4. Rank priority by its position in the rule's classification order (`priority_rank`)
5. Assign workflow stage and stage type
6. Explode matching contexts into multiple logical rows
7. Validate issues against configured rules
8. Merge orphan-context handling into both analytics and quality outputs

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

`issues_valid.parquet` is always rewritten as well, as an empty file when no issue is valid or when no Layer 1 issue files exist. A full sync that returns no issues deletes the project's Layer 1 file, so without this the dashboard would keep showing issues that no longer exist in GitLab.

## 4. Data Outputs

| File | Content |
| :---- | :---- |
| `data/analytics/issues_valid.parquet` | Enriched analytics dataset |
| `data/analytics/data_quality.parquet` | Validation and quality hints |

## 5. Rationale

- **Modular YAML rules:** different teams can tailor interpretation without changing processor code
- **User rules in `data/rules/`, template in `app/config/rules/`:** rules saved from the dashboard must survive a Docker image rebuild and must not modify tracked files in a git checkout. `data/` is already the mounted, gitignored volume, so user rules live there and the shipped file stays an untouched template.
- **Rule store in Layer 2, not in the dashboard:** the processor owns the rule file format (`DomainRule`), so reading, validating, and writing it sit next to the loader; the dashboard only translates between HTTP and the store.
- **Regenerated files instead of comment-preserving edits:** the Settings screen is the primary editor, so saved files are written from the model with PyYAML. Keeping comments would need a round-trip YAML library for a file users are no longer expected to open.
- **Split analytics vs. quality output:** analytics stays usable while quality issues remain actionable
- **Context explosion in Layer 2:** avoids repeated label parsing in the UI layer
