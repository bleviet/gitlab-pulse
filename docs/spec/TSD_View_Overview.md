# Technical Specification: Overview View

**Status:** Implemented  
**Scope:** Current behavior of the primary dashboard view in `frontend/src/App.tsx`, `frontend/src/components/AnalyticsView.tsx`, and `frontend/src/components/IssuePanel.tsx`.

## 1. Purpose

The Overview page is the main workflow health view. It combines issue flow, milestone timing, quality signals, and issue drill-down into a single curated screen.

## 2. Data Model Assumptions

The page renders from the Layer 2 analytics dataset and uses deduplicated issue IDs for headline visualizations where multi-context duplication would otherwise distort counts.

It also accepts:

- `quality_df` for supporting quality signals
- `stage_descriptions` from the loaded rule set
- `timeline_df` so milestone visuals can use pre-milestone-filter data

## 3. Layouts

The Overview has two layouts that share one issue board, one filter (4.1) and one URL format. An "Analytics | Compact" switch at the top right of the sticky navigation bar changes the layout. The choice is kept in session state and in the URL (`?view=compact`). The filter carries over when switching.

| Layout | Purpose | Above the board |
|---|---|---|
| Analytics (default) | Stepping back: trends, review meetings, reports | The chart grid and pinned workflow-state row (3.4) |
| Compact | Daily triage: as many cards on screen as possible | A thin release rail; the summary pills share the board's toolbar row (3.1 to 3.3) |

### 3.0 Compact layout

One column, one focus: the issue board, which starts high on the screen. Nothing competes with the board for width or height, so the page works consistently from laptop screens to ultrawide monitors.

| Row | Content |
|---|---|
| Releases | The milestone timeline as a thin rail with its label inside (3.1) |
| Board toolbar | Summary pills on the left (3.2); search (`Ctrl/Cmd+K`) and the Table/Board switch on the right |
| Filter chips | Only while the board is filtered: one chip per filter, "Clear all", and the issue count. They share the row with the page bar on the right |
| Lanes | The board; the workflow state is shown in its lane headers (3.3) |

- The global Filters drawer (`SidebarDrawer`) is collapsed by default and opens from the top-left Filters button (displaying a badge when sidebar filters are active); active sidebar filters also appear as removable chips on the board in Compact layout.
- On a narrow window the lanes keep a minimum width of 15rem and the board scrolls sideways, instead of squeezing the cards.
- A lane is as tall as its page of cards (no scrolling inside, see Paging in 4.3); the lanes of a row stretch to the tallest. A lane wider than two cards (large screens) shows its cards in several columns.

### 3.1 Release rail

`ReleaseTimeline` (`frontend/src/components/charts/ReleaseTimeline.tsx`) with `variant="compact"`: a soft band with a centre rail, round markers coloured by status (complete, incomplete, on track, overdue) that alternate above and below the rail in date order, their names next to them, and a pink line labelled "NOW" for today. Active milestones without a due date are drawn as neutral "Unscheduled" markers in a "No due date" section after the latest dated milestone (at least 90 days ahead), in natural version order (`v2.4.9` before `v2.4.10`); their hover shows "Due: Not set". Closed milestones without a due date are hidden. Clicking a milestone sets the milestone filter (4.2).

### 3.2 Summary pills

`SummaryBar` (`frontend/src/components/SummaryBar.tsx`), rendered in the left part of the board's toolbar row using counts computed by `buildSummaryGroups` (`frontend/src/lib/summary.ts`) from issues after the sidebar filters, independent of the board's facets.

| Group | Pill | Count | Board filter |
|---|---|---|---|
| Flow | Open | open issues | open issues |
| | New 7d | issues created in the last 7 days | created in the last 7 days, any state |
| | Closed 7d | issues closed in the last 7 days | closed in the last 7 days |
| Open by priority | P1, P2, ... Unset | open issues per priority, ordered by `priority_rank`, "Unset" last, each with a coloured dot | open issues of that priority |
| Hints | No milestone, Unassigned, Mixed | open issues with that quality signal | that quality signal |

There is no pill for all closed issues; in the Analytics layout, a click in the centre of the closed-issues donut selects them.

Picking a pill replaces the board's filter (the search text is kept) and shows the pill as pressed; picking it again resets the board to all open issues.

### 3.3 Lane headers

Each lane header (`frontend/src/components/IssueBoard.tsx`) renders directly above its lane:

- the stage name and the number of cards in the lane,
- a thin stacked bar of the lane's issues by priority,
- one compact pill per priority: a coloured dot and the count. The dot colours follow `priority_rank` (`buildPriorityColorMap`) and match the summary's priority pills.

The header counts ignore the stage and priority filters, so every lane keeps its full priority mix. Picking a lane pill refines the current filter with that stage and priority (and open issues, unless a state is set); picking it again removes the refinement.

### 3.4 Analytics layout

`AnalyticsView` (`frontend/src/components/AnalyticsView.tsx`) renders three rows of SVG chart panels above the issue panel:

| Row | Panels |
|---|---|
| 1 | Release Timeline (span 9), Closed Issues by Priority (donut, span 3) |
| 2 | Open Issues by Priority (donut, span 3), Issue Quality Signals (span 3), Daily New vs. Closed Issues (7 days, span 6) |
| 3 | Issues by Workflow State (priority bars per stage); stays pinned below the header while the board scrolls |

How pinning and selection work:

- Native CSS `position: sticky` keeps the workflow-state row pinned below the top navbar (`--nav-height`) and pins the issue panel toolbar/page bar (`--workflow-sticky-h`) beneath it whenever the viewport has sufficient vertical room (`>= 250px` below the pinned row).
- Clicking any chart segment (`PriorityDonut` slice or center, `QualitySignalsChart` bar, `DailyVelocityChart` point, or `WorkflowStateRow` bar) updates `facets` and sets `activeChart`, dimming sibling segments cleanly. Clicking the active segment again or clicking the `"Chart filter active"` chip clears the filter while preserving search text.

## 4. Interactions

### 4.1 Board filter

The board is always visible and shows all open issues until something filters it. Its filter is a set of facets (`stage`, `state`, `priority`, `signal`, `recent`, `day` with `day_kind`, `query`) in `frontend/src/lib/facets.ts`:

- a summary pill sets the base facets (3.2),
- a lane pill adds `stage` and `priority` (3.3),
- a chart click in the Analytics layout sets the facets the segment stands for: a donut slice its state and priority, a donut centre its state, a workflow-state bar its stage, open state and priority, a velocity point the day and created/closed, and a quality bar the signal (3.4),
- the search field in the board's toolbar sets `query` (4.5).

Open issues are the default: a missing `state` means `opened`, and only `closed` or `all` is shown as a chip (not next to a 7-day filter, which already says which issues it covers).

While the board is filtered, a row under the toolbar shows one removable chip per facet and per active sidebar filter (team, context, milestone, time range), "Clear all" and the issue count.

### 4.1.1 URL state

The facets and the picked summary pill are mirrored into query parameters (`summary`, `f_stage`, `f_state`, `f_priority`, `f_signal`, `f_recent`, `f_day`, `f_day_kind`, `f_query`; the layout uses `view`), so a refresh or a shared link restores the same view. The URL is only read when it differs from what the session last wrote, which is the case on page load. Malformed values are ignored. Sidebar filters are not part of the URL.

### 4.2 Milestone synchronization

The release timeline and sidebar milestone selector are synchronized bidirectionally through session state. Selecting a milestone from the timeline updates the sidebar filter, and clearing the sidebar resets timeline selection state.

### 4.3 Issue board and table

The issue panel (`frontend/src/components/IssuePanel.tsx`) opens as the Table; users switch between Table and Board directly in the toolbar.

**Paging.** The page bar on the right of the chips row sets how much is shown, with previous/next buttons when there is more than one page. The table's sizes are `Fit` (default), `10`, `20`, and `30`; the board shows `10` (default), `20`, or `30` cards per lane.

Fit measures the available viewport height below the panel head via a `ResizeObserver` and window resize listener (clamped to 5–100 rows), avoiding polling timers.

- **Table** (`IssueTable.tsx`, `@tanstack/react-table`): sticky column headers with client-side sorting and hierarchical parent-before-child ordering by default.
- **Board** (`IssueBoard.tsx`): lanes aligned to workflow stages with horizontal scroll syncing between lane headers and lanes.

### 4.5 Search field (Ctrl/Cmd+K)

`IssueSearchInput` (`frontend/src/components/IssueSearchInput.tsx`) renders directly in the toolbar DOM, widens on focus or non-empty text, focuses on `Ctrl/Cmd+K`, blurs on `Escape`, and filters client-side via `filterIssuesBySearch` (`frontend/src/lib/search.ts`) with exact multi-token matching and typo-tolerant fuzzy fallback.

### 4.6 Reactive Execution Model

The FastAPI endpoint `/api/dashboard` returns the collapsed issue dataset once (cached by file mtime in `DashboardService`). All filtering, sorting, paging, summary counts, and SVG chart rendering run synchronously in React `useMemo` hooks without server round-trips.

## 5. Notes on Scope

- The Overview page (Compact and Analytics layouts) is the sole presentation view; the legacy Custom View layout builder has been removed.
