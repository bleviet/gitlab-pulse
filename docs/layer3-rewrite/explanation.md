# Explanation: Why Layer 3 Was Rewritten with FastAPI and React/TypeScript

This document explains the architectural reasons behind rewriting Layer 3 on branch `feat/fastapi-react-dashboard`, why specific alternatives were chosen, and why parts of the previous system were removed.

## 1. Problems With the Previous Streamlit Implementation

Streamlit worked well when GitLab Pulse was a small read-only metrics viewer over Layer 2 Parquet files. As the dashboard evolved into an interactive issue-triage workspace—with a Kanban board, cross-filtered charts, `Ctrl/Cmd+K` search, URL-synced filters, sticky multi-row headers, and light/dark brand theming—the Layer 3 directory grew to roughly 8,000 lines across 43 Python files and hit four structural limits in Streamlit's execution and DOM model:

1. **Top-to-bottom script reruns on every interaction.**
   Streamlit re-executes the Python script when widgets change. Even after isolating the board inside `@st.fragment` (`_issue_panel_fragment` and `_analytics_fragment`), cross-filtering across Plotly charts required maintaining explicit widget-key reset counters (`timeline_reset_counter`, `issue_chart_resets`), serializing prior selection payloads into `issue_chart_signatures`, tracking confirmation state (`issue_chart_confirmed`), and draining pending session-state keys before sidebar widgets instantiated.

2. **Cross-iframe and polling workarounds.**
   Because Streamlit isolates custom components in iframes and redraws its own DOM nodes:
   - `pinned_header.py` ran a 500 ms `setInterval` loop to measure element heights into CSS variables (`--pulse-pin-top`, `--pulse-board-top`, `--pulse-heads-top`), sync horizontal `scrollLeft` across lanes and headers, and copy the `st.dataframe` canvas header onto a non-interactive `<canvas id="pulse-table-head">`.
   - `issue_search.py` wrapped `st_keyup` inside a same-origin iframe, requiring a `MutationObserver` and a 500 ms `setInterval` piercing `iframe.contentDocument` to inject pill styles, capture `Ctrl/Cmd+K` and `Escape`, and toggle `data-active`/`data-filled` attributes.
   - `theme.py` included `inject_theme_watcher()`, polling computed styles every 500 ms inside a hidden iframe to call `parent.location.reload()` when the user toggled light/dark mode because `st.context.theme` did not update in place.
   - `issue_pages.py` mounted a custom Fit probe component polling layout heights to calculate how many table rows fit in the viewport.

3. **Fragility of the hybrid Custom View engine.**
   The experimental layout builder (`engine.py`) depended on `streamlit-elements` (which rendered placeholder `mui.Paper` blueprint cards in Edit Mode while View Mode fell back to native `st.columns`) and parsed serialized frame JSON out of `st.session_state`.

4. **DOM and server-round-trip latency on the Kanban board.**
   Rendering each card in `issue_board.py` created a `st.container` plus three `st.markdown(..., unsafe_allow_html=True)` elements per card on the server, requiring server-side paging and figure caching (`figure_cache.py`) to keep click latency bounded.

## 2. Why FastAPI + React/TypeScript Was Chosen

We evaluated three options:

- **Stay on Streamlit and trim scope:** lowest short-term effort, but keeps the top-to-bottom rerun model and iframe isolation for search and charts.
- **Pure-Python reactive frameworks (NiceGUI or Plotly Dash):** removes script reruns, but still constrains custom Kanban layouts, sticky multi-row synchronization, and tight brand styling compared to standard web tooling.
- **Thin FastAPI API + React/TypeScript SPA:** cleanly separates data loading from UI state.

We chose **FastAPI + React/TypeScript** because:

- **Interactive state belongs in the browser.** Filter facets, `Ctrl/Cmd+K` search, column sorting, pagination, Fit row sizing, theme switching, and chart selection highlighting update synchronously in memory within a few milliseconds without server round-trips.
- **Native browser layout removes polling scripts.** Standard CSS `position: sticky` keeps headers, toolbars, and Analytics workflow bars pinned; React refs sync board lane headers on `scroll` events directly; and CSS custom properties (`:root` / `[data-theme="light"]`) switch themes instantly with zero page reloads.
- **Preserves Layers 1 and 2 untouched.** Because `app/collector/` and `app/processor/` write Parquet files and never import Layer 3 (`AGENTS.md` Rule 1), replacing `app/dashboard/` left ingestion, rules, enrichment, and validation intact.
- **Single-process local deployment remains simple.** FastAPI serves both `/api/*` endpoints and the compiled static bundle (`frontend/dist/`), so users still launch the entire dashboard with one command (`uv run python -m app.dashboard` on port `8501`).

## 3. Rationale for Specific Design Decisions

### Client-side filtering over per-click API queries
GitLab Pulse operates on local project datasets typically in the hundreds to low thousands of issues (the local seeded dataset is 3,000 issues across 3,065 context-exploded rows). Collapsing exploded contexts on the server and omitting heavy text fields (`description`, `notes`) produces a GZip-compressed JSON payload returned once from `/api/dashboard`. Keeping filtering (`facets.ts`), fuzzy search (`search.ts`), summary counts (`summary.ts`), and chart binning (`analytics.ts`, `timeline.ts`) in pure TypeScript eliminates network latency on every click and makes all filter logic unit-testable with Vitest.

### Custom React SVG charts over Plotly.js or ECharts
The dashboard uses five focused chart types (milestone release rail, priority donut with clickable center, horizontal quality-signal bars, 7-day dual velocity line, and per-stage workflow bars). Writing them directly as responsive React SVG components using `ResizeObserver` avoids shipping a multi-megabyte charting bundle, eliminates the Plotly `Scatter` workaround previously needed in `priority_donut.py` to make donut slices and centers clickable, and binds colors directly to CSS variables and YAML palette overrides.

### Removing Custom View and unifying Analytics + Compact into one workspace
Removing `engine.py`, `registry.py`, `data/config/layouts/`, and deprecated standalone chart/KPI widgets drops unmaintained `streamlit-elements` dependencies. Rather than maintaining two diverging page layouts (`Analytics` and `Compact`), the React SPA merges them into a single `100vh` `OverviewWorkspace` controlled by a **Charts** toggle:

- **Charts ON (default):** opens directly on release progress, open priority and type mix, workflow-state bottlenecks (including closed terminal stages), 7-day flow velocity, and open quality hints. Moving the release timeline to a persistent `78 px` full-width strip, combining Open Priority and Open Issue Type donuts with shared clickable legends into one `Open Mix` card, placing `Workflow State` directly underneath so the priority palette reads continuously from totals to stages, merging the toolbar and pager into a single row, and switching between a `380 px` left analytics rail (on `>= 1360px` screens in Table view) and a single 4-card top bento strip (on narrower viewports or Kanban Board view) keeps every chart interactive while dedicating full vertical height to the issue list.
- **Charts OFF (`?view=compact`):** hides the four analytics cards, keeps the `78 px` Release Rail visible at the top, automatically surfaces `SummaryBar` quick-filter pills inside the issue panel, and gives the remaining viewport height to the issue table or Kanban board. Named removable filter chips stay visible in both modes so active chart, summary, lane, search, and global scope filters are always transparent and individually removable.

### File-mtime caching in `DashboardService`
Instead of Streamlit's 2-minute TTL (`@st.cache_data(ttl=120)`), `DashboardService` keys its in-memory cache on `st_mtime_ns` of `issues_valid.parquet`, `labels_*.parquet`, `sync_state.json`, and the active rule files (`data/rules/*.yaml`, or `app/config/rules/*.yaml` while `data/rules/` has no rule files). Unchanged datasets return immediately from memory while external runs of `app/processor/main.py` or `tools/local_data_manager.py` become visible on the next request without waiting for a TTL to expire.
