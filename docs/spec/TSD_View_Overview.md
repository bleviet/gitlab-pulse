# Technical Specification: Overview View

**Status:** Implemented  
**Scope:** Current behavior of the primary curated dashboard page in `app/dashboard/views/overview.py`.

## 1. Purpose

The Overview page is the main workflow health view. It combines issue flow, milestone timing, quality signals, and issue drill-down into a single curated screen.

## 2. Data Model Assumptions

The page renders from the Layer 2 analytics dataset and uses deduplicated issue IDs for headline visualizations where multi-context duplication would otherwise distort counts.

It also accepts:

- `quality_df` for supporting quality signals
- `stage_descriptions` from the loaded rule set
- `timeline_df` so milestone visuals can use pre-milestone-filter data

## 3. Current Panels

### 3.1 Row 1

- **Open Issues by Priority**
- **Closed Issues by Priority**
- **Daily New vs. Closed Issues**

### 3.2 Row 2

- **Issues by Workflow State**

This panel reflects configured workflow stage order when available.

### 3.3 Row 3

- **Release Timeline**
- **Open vs. Closed Issues**
- **Issue Quality Signals**

## 4. Interactions

### 4.1 Chart-driven drill-down

Multiple charts return selection payloads. When the user clicks into a chart, the page opens a filtered issue dialog backed by the same analytics dataset.

### 4.2 Milestone synchronization

The release timeline and sidebar milestone selector are synchronized bidirectionally through session state. Selecting a milestone from the timeline updates the sidebar filter, and clearing the sidebar resets timeline selection state.

### 4.3 Issue drill-down table

The issue table supports:

- single-row selection
- fuzzy search across normalized issue text
- AI status markers:
  - `✨` means no persisted AI summary yet
  - `📝` means AI data exists in `data/ai/`
- clickable issue links
- optional context and quality-hint display

Selecting a row persists the issue URL in session state and opens the detail flow.

### 4.4 Local seeded issue details

For locally seeded issues, the detail flow resolves from local parquet-backed data rather than assuming a live GitLab API lookup. This keeps local demo workflows usable end-to-end.

## 5. AI Integration

The Overview drill-down flow is the primary place where the AI assistant is exposed today. From the selected issue, the user can:

- see whether AI content exists
- generate a summary
- view the current summary
- continue a chat tied to that issue

## 6. Notes on Scope

- The active top-level page name is **Overview**
- Overview is intentionally curated; it is not the same surface as the generic custom layout builder
