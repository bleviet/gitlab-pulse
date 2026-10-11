# AGENTS.md

Canonical instructions for every coding agent working in this repository
(Codex, Gemini CLI, Claude Code, Antigravity, Copilot, OpenCode, ...). Tool
entry points only point here; see [Agent configuration layout](#agent-configuration-layout).

GitLab Pulse is a local-first Streamlit analytics application for GitLab issue
data. A collector pulls issues from the GitLab REST/GraphQL APIs (or a seeder
generates synthetic data), a processor enriches and validates them against YAML
rules into Parquet, and a Streamlit dashboard renders them, with optional local
AI summaries and chat via Ollama.

## Commands

All Python runs through `uv`. Always use `uv run <command>`; never source
`.venv/bin/activate` (it does not persist across non-interactive agent shells).

```bash
uv sync                                              # Install dependencies (incl. dev group)
uv run python app/collector/orchestrator.py          # Layer 1: fetch from GitLab (--project-ids, --full-sync)
uv run python app/processor/main.py                  # Layer 2: enrich + validate into data/analytics/
uv run streamlit run app/dashboard/main.py           # Layer 3: dashboard on :8501
uv run python tools/local_data_manager.py            # Seed / inspect / delete synthetic local data

uv run pytest                                        # All tests (tests/, config in pyproject.toml)
uv run pytest tests/test_validator.py -k missing     # Targeted test
uv run ruff check <files>                            # Lint
uv run mypy <files>                                  # Type check (strict)
```

The repository has pre-existing `ruff` and `mypy` findings. Do not fix them
outside the scope of the task, but do not add new ones: lint and type-check the
files you touched and compare against `git stash`/baseline output if in doubt.
`pytest` must stay fully green.

## Architecture

Layered data pipeline (`docs/architecture/ARCH_Master.md` is the reference;
per-layer specs are in `docs/spec/TSD_*.md`):

| Layer | Code | Output |
|---|---|---|
| 0 Raw | `app/collector/` | `data/raw/*.json` (audit copy of API payloads) |
| 1 Processed | `app/collector/` (`orchestrator.py`, `rest_client.py`, `gql_client.py`, `state.py`) | `data/processed/{issues,milestones,labels}_<project_id>.parquet`, `data/state/sync_state.json` |
| 2 Analytics | `app/processor/` (`enricher.py`, `validator.py`, `rule_loader.py`) | `data/analytics/issues_valid.parquet`, `data/analytics/data_quality.parquet` |
| 3 Presentation | `app/dashboard/` (Streamlit) | UI; layouts in `data/config/layouts/*.json` |
| 4 AI | `app/ai/` (Ollama) | `data/ai/*.parquet` (summaries, chat history) |

Shared Pydantic schemas live in `app/shared/schemas.py`. Rules are YAML files in
`app/config/rules/` (`default.yaml` is the template); `RuleLoader` discovers
them, and a rule file may restrict itself to `project_ids`.

### Architecture rules (binding)

1. **Dependencies point downward.** Dashboard reads analytics data; processor
   reads processed data; collector knows nothing about business rules. Layer 1
   must never import from `app/processor/` or `app/dashboard/`, and Layer 2
   must never import from `app/dashboard/`. No circular imports.
2. **One schema definition.** Parquet writers and readers import the same model
   from `app/shared/schemas.py` (or `app/collector/models.py`). Do not redefine
   columns or field names locally.
3. **Extend, don't modify.** New metrics are new enricher functions registered
   in the processing pipeline, not new fields hacked onto `RawIssue`. New teams
   or projects are new rule YAML files, not code changes in `main.py`.
4. **Vectorize.** Never use `df.iterrows()` or Python loops over DataFrames; use
   vectorized pandas operations. Use `category` dtype for low-cardinality
   string columns.
5. **Dates are UTC.** Normalize every timestamp to tz-aware UTC before
   arithmetic (GitLab.com and self-hosted instances differ). Prefer
   `pd.to_datetime(..., utc=True)` / Pydantic `datetime` fields over ad-hoc
   `strptime` calls.
6. **Atomic writes.** Persist files by writing to `*.tmp` and `os.replace`-ing
   into place, as `processor/main.py`, `collector/rest_client.py`, and
   `collector/state.py` already do.
7. **Fail per unit, not globally.** A failing project (e.g. 403) is logged and
   skipped; a malformed rule file skips that team. A collector `404` with an
   existing `issues_<id>.parquet` is treated as local seeded data.
8. **Dashboard composition.** Widgets are pure render functions
   `(df, config) -> ...` under `app/dashboard/widgets/{charts,kpis,tables,features}/`,
   exported from their package `__init__.py` and registered by string ID in
   `app/dashboard/registry.py`. Views (`app/dashboard/views/`) compose
   widgets; they should not accumulate data transformations. Keep modules
   cohesive and treat ~400-500 lines as a review signal for extraction
   (`views/overview.py` is already well past it; do not grow it further
   without extracting).
9. **Preserve behavior during refactors.** Session-state keys, cache TTLs,
   widget keys, and layout JSON shape are user-visible contracts. For risky
   refactors, first add characterization tests at the current boundary.

### Theming (binding)

- UI chrome colors (backgrounds, text, borders, primary, fonts) belong in
  `.streamlit/config.toml` (`[theme.light]` / `[theme.dark]`).
- Semantic data colors (severity, issue type, stage) and Plotly styling belong
  in `app/dashboard/theme.py`. Never hardcode colors in widgets; use
  `get_palette()`, `get_severity_colors()`, `get_stage_colors()`,
  `plotly_layout(...)`, and `plotly_bar_trace_style()`.
- Keep injected CSS (`get_global_css()`) minimal and limited to what
  `config.toml` cannot express. Both light and dark must render correctly.
- The palette and fonts follow the bahonavi brand; see the `brand-guidelines`
  and `frontend-design` skills before visual changes.

## Key conventions

- **Python style:** PEP 8, ruff config in `pyproject.toml` (line length 88,
  py311). `.editorconfig` governs whitespace: 4-space Python, 2-space
  YAML/JSON/web files, LF, trailing whitespace trimmed (except Markdown).
- **Types:** type hints on every function signature; mypy runs in strict mode.
  No `Any` in core pipeline logic.
- **Pydantic v2** for DTOs: `@field_validator` for single fields,
  `@model_validator(mode="after")` for cross-field rules, `frozen=True` for
  config models.
- **Imports:** absolute (`from app.dashboard.theme import ...`), not relative.
- **Docstrings:** Google style on public APIs.
- **Streamlit width:** use `width="stretch"` for `st.plotly_chart` and
  `st.dataframe`, never the deprecated `use_container_width=True`. Existing
  occurrences are legacy; convert only the ones you touch.
- **Caching:** data loaders use `@st.cache_data` with short TTLs; keep them
  consistent with `app/dashboard/data_loader.py`.
- **Match surrounding code.** Follow the naming and idiom of the file you edit.
- **No commented-out code.** Delete it.
- **Dependencies:** add them with `uv add` (or `uv add --dev`); do not bump
  existing ones unless the task asks for it.

### Tests

`tests/` (pytest). Validators are tested with fixture issues (a valid issue, a
broken one) asserting how they are classified. Use the seeder or
`tools/local_data_manager.py` for realistic local data instead of live GitLab;
never commit generated `data/` content (only `.gitkeep` and
`data/config/layouts/default.json` are tracked).

## Working rules

- **Think first.** If a contract is ambiguous or conflicts with the
  architecture above, ask the user instead of guessing. A delegated subagent
  stops and reports back to its orchestrator instead.
- **Simplicity.** Minimum code for the task. No over-engineering, speculative
  options, single-use wrappers, unrequested features, or unnecessary defensive
  checks.
- **Surgical diffs.** Every changed line traces to the task. No reformatting,
  import reshuffles, or comment edits outside scope; remove only dead code your
  change created.
- **Root cause, with evidence.** Before fixing a bug, prove the root cause,
  write a failing reproduction test, fix the root cause (not the symptom), and
  show the test and the suite passing.
- **Verify before reporting done.** Run the targeted tests, `uv run pytest`,
  and `uv run ruff check` / `uv run mypy` on the touched files.
- **Version control.** Never add, commit, push, or merge automatically; let the
  developer review first. Commit messages use Conventional Commits
  (`feat`, `fix`, `docs`, `chore`, `test`, `refactor`). Never commit secrets
  (`.env`) or generated data.

## Documentation

- Plain, technical, honest tone. No marketing language, buzzwords, or
  exaggerated claims; write the way an engineer explains the system to another
  engineer. No emojis in documentation.
- **Usage ("how")** goes in `README.md` and docstrings. **Architecture
  ("why")** goes in `docs/architecture/`, per-layer specs in `docs/spec/`,
  guides in `docs/guidelines/`. Planning and working docs go in `docs/`, never
  at the repo root.
- Architecture docs must state the rationale for major decisions, e.g. "We
  chose Pydantic over dataclasses because user-provided YAML needs runtime
  validation and coercion", not just "We use Pydantic".
- Keep the README and docs in sync when behavior changes.
  `docs/guidelines/GUIDE_Developer.md` has longer examples for the conventions
  above.

## Agent configuration layout

`AGENTS.md` is the single source of instructions. Skills follow the Agent
Skills `SKILL.md` format and live once, in `.agents/skills/`. Tool-specific
files only point at these; put shared guidance here, never in them.

| Path | Purpose | Read by |
|---|---|---|
| `AGENTS.md` | Canonical instructions (this file) | Codex, Antigravity, Copilot, OpenCode, Cursor; Gemini CLI via `.gemini/settings.json`; Claude Code via `CLAUDE.md` import |
| `.agents/skills/<name>/SKILL.md` | Shared on-demand skills | Codex, Gemini CLI, Antigravity, OpenCode, Copilot; Claude Code via `.claude/skills/` symlinks |
| `.gemini/settings.json` | Points Gemini CLI at `AGENTS.md` | Gemini CLI |
| `CLAUDE.md` | Imports `AGENTS.md`, adds the Claude-only delegation workflow | Claude Code |
| `.claude/skills/<name>` | Symlinks to `.agents/skills/<name>` | Claude Code |
| `.claude/agents/` | Claude-only `coder`/`reviewer` subagents (model and tool pins; role prompts live in `.agents/skills/orchestrate/references/`) | Claude Code |

Available skills: `orchestrate` (plan -> implement -> audit),
`local-data-manager` (synthetic data workflow), `brand-guidelines` and
`frontend-design` (bahonavi visual identity for the dashboard and other UI).

Plan -> implement -> audit for non-trivial changes is the shared
`orchestrate` skill (`/orchestrate`). Tools with subagents dispatch the
`coder` and `reviewer` roles to them; tools without subagents run the phases
in sequence, with the audit as a separate read-only pass.

To add a skill, create `.agents/skills/<name>/SKILL.md` and link it for Claude
Code: `ln -s ../../.agents/skills/<name> .claude/skills/<name>`. On Windows,
clone with `git config core.symlinks true` (Developer Mode) or the links
check out as plain text files.
