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

## 3. Unified Workspace Modes

The Overview uses one `100vh` workspace (`OverviewWorkspace` in `frontend/src/components/OverviewWorkspace.tsx`) controlled by a **Charts** toggle in the top-right navigation bar. Active facets and sidebar filters persist across toggles, and hiding charts sets `?view=compact` in the URL for shareability and backwards compatibility.

| State | Purpose | Above / Beside the Issue Panel |
|---|---|---|
| Charts ON (default) | Visual flow & review cockpit | Persistent `72 px` Release Rail + `380 px` left analytics rail (`>= 1360px` Table) or 4-card top bento strip (`< 1360px` / Board) |
| Charts OFF (`?view=compact`) | High-density daily triage | Persistent `72 px` Release Rail + `SummaryBar` quick-filter pills (`Flow`, `Open by priority`, `Hints`) inside the panel header |

- The global Filters drawer (`SidebarDrawer`) is collapsed by default and opens from the top-left Filters button (displaying a badge when sidebar filters are active); active sidebar filters and board facets always appear as named removable chips in the issue panel toolbar.
- On a narrow window, board lanes keep a minimum width of 15rem and scroll sideways instead of squeezing cards; wide lanes wrap cards into multiple columns.

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

### 3.4 Responsive Hybrid Charts Layout

When **Charts** is ON, `OverviewWorkspace` (`frontend/src/components/OverviewWorkspace.tsx`) renders a single-viewport (`100vh`) responsive hybrid cockpit:

- **Top strip (full width):** `ReleaseTimeline` in compact rail style (`78 px` height, always visible whether Charts is ON or OFF).
- **Wide desktop (`>= 1360px` in Table view):** two-column split with a `380 px` left analytics rail (`Open Mix` with side-by-side Open Priority and Open Type donuts plus clickable color legends, horizontal stacked `Workflow State` bars across open stages and closed terminal stages with inline priority counts, `Daily New vs. Closed`, and `Issue Quality Signals`) beside the full-height `IssuePanel`.
- **Narrower viewports (`< 1360px`) or Kanban Board view:** collapses to a single 4-card bento strip above `IssuePanel` so the board or table uses full horizontal width.
- **Unified toolbar:** `IssuePanel` displays the issue count and named removable filter chips (`Clear all` when filtered) on the left, with search (`Ctrl/Cmd+K`), Table/Board switch, and `Fit`/10/20/30 paging on the right. `Fit` computes row counts from the panel body height so the table fills the remaining viewport without page scrolling.
- Clicking any chart segment (`PriorityDonut` slice, legend item, or center, `WorkflowStateRow` stage label / priority segment, `DailyVelocityChart` point, or `QualitySignalsChart` bar) updates `facets` and sets `activeChart`, dimming sibling elements cleanly. Clicking the active target again or removing its named chip clears the filter while preserving search text.

## 4. Interactions

### 4.1 Board filter

The board is always visible and shows all open issues until something filters it. Its filter is a set of facets (`stage`, `state`, `priority`, `issue_type`, `signal`, `recent`, `day` with `day_kind`, `query`) in `frontend/src/lib/facets.ts`:

- a summary pill sets the base facets (3.2),
- a lane pill adds `stage` and `priority` (3.3),
- a chart click in the Analytics layout sets the facets the segment stands for: an `Open Mix` slice or legend item sets open `state` with its `priority` or `issue_type` (and the donut center selects all open issues), a workflow-state bar sets its stage, bucket state (`opened`, `closed`, or `all`), and priority, a velocity point sets the day and `created` (`state: "all"`) or `closed` (`state: "closed"`), and a quality bar sets the signal on open issues (3.4),
- the search field in the board's toolbar sets `query` (4.5).

Open issues are the default: a missing `state` means `opened`, and only `closed` or `all` is shown as a chip (not next to a 7-day filter, which already says which issues it covers).

While the board is filtered, a row under the toolbar shows one removable chip per facet and per active sidebar filter (team, context, milestone, time range), "Clear all" and the issue count.

### 4.1.1 URL state

The facets and the picked summary pill are mirrored into query parameters (`summary`, `f_stage`, `f_state`, `f_priority`, `f_issue_type`, `f_signal`, `f_recent`, `f_day`, `f_day_kind`, `f_query`; the layout uses `view`), so a refresh or a shared link restores the same view. The URL is only read when it differs from what the session last wrote, which is the case on page load. Malformed values are ignored. Sidebar filters are not part of the URL.

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

- The unified Overview workspace (with toggleable Charts and persistent Release Rail) is the sole presentation view; the legacy Custom View layout builder has been removed.
