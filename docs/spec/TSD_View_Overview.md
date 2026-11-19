# Technical Specification: Overview View

**Status:** Implemented  
**Scope:** Current behavior of the primary dashboard view in `frontend/src/App.tsx`, `frontend/src/components/OverviewWorkspace.tsx`, `frontend/src/components/ScopeBar.tsx`, and `frontend/src/components/IssuePanel.tsx`.

## 1. Purpose

The Overview page is the main workflow health view. It combines issue flow, milestone timing, quality signals, and issue drill-down into a single curated screen.

## 2. Data Model Assumptions

The page renders from the Layer 2 analytics dataset and uses deduplicated issue IDs for headline visualizations where multi-context duplication would otherwise distort counts.

It also accepts:

- `quality_df` for supporting quality signals
- `stage_descriptions` from the loaded rule set
- `timeline_df` so milestone visuals can use pre-milestone-filter data

## 3. Unified Workspace Modes

The Overview uses one `100vh` workspace (`OverviewWorkspace` in `frontend/src/components/OverviewWorkspace.tsx`) controlled by a **Charts** toggle in the top-right navigation bar. Active facets and global scope filters persist across toggles and in URL query parameters (`?view=compact` when charts are hidden, plus `g_*` and `f_*`) for shareability and backwards compatibility.

| State | Purpose | Above / Beside the Issue Panel |
|---|---|---|
| Charts ON (default) | Visual flow & review cockpit | Persistent `78 px` Release Rail + `380 px` left analytics rail (`>= 1360px` Table) or 4-card top bento strip (`< 1360px` / Board) |
| Charts OFF (`?view=compact`) | High-density daily triage | Persistent `78 px` Release Rail + `SummaryBar` quick-filter pills (`Flow`, `Open by priority`, `Hints`) inside the panel header |

- Global scope filters (`ScopeBar` in `TopBar`) stay inline across screen sizes, combining a unified tokenized fuzzy scope picker (`Context`, `Milestone`, and `Team` when multiple exist—supporting multi-term queries such as `proj v14` and quick-apply pairs) with inline `30d`/`90d`/`1y`/`All` presets and a custom date popover (wrapping onto a second bar row below `960 px` instead of hiding behind a drawer or Filters button); active global scopes and board facets always appear as named removable chips in the issue panel toolbar.
- An ambient refresh/sync status button in `TopBar` exposes sync health, last sync timestamp, and app version on hover and triggers data reload on click.
- On a narrow window, board lanes keep a minimum width of 15rem and scroll sideways instead of squeezing cards; wide lanes wrap cards into multiple columns.

### 3.1 Release rail

`ReleaseTimeline` (`frontend/src/components/charts/ReleaseTimeline.tsx`) with `variant="compact"`: a soft band with a centre rail, round markers coloured by status (complete, incomplete, on track, overdue) that alternate above and below the rail in date order, their names next to them, and a pink line labelled "NOW" for today. The rail shows only milestones with a due date (a milestone counts as dated when any of its issues carries one); hover shows "Due:" with the ISO date. Month ticks sit on UTC month starts and step every k months so they fit the width. By default the date scale covers a one-year window, today − 182 days to today + 183 days. Centring the window keeps the next planned release visible even when it is months away, and a placeholder due date far in the future (for example `2100-01-01`) no longer compresses the scale. Dated milestones outside the window are left off the scale and counted instead: "‹ N earlier" sits at the left end of the tick row and "N later ›" at the right end, each shown only when N is non-zero. Clicking either switches to show-all, which fits the scale to every dated milestone; in that mode "1 year ›" at the right end switches back. The controls are keyboard accessible (`role="button"`, Enter/Space), and tick labels that would collide with a control are hidden. A milestone selected in the milestone filter stays on the rail even when it falls outside the window, and the window widens to include it. The show-all choice is local component state; it is not persisted and resets on reload. Milestones without a due date are not placed on the date scale. When any exist, a tray at the right end of the rail, outside the date scale, shows "{N} unscheduled" and "{M} open issues" (`120 px`; below `520 px` chart width a compact `56 px` tray shows only the ring and N). The tray is a button whenever unscheduled milestones exist, with Charts on or off. In the wide split it scrolls the Unscheduled Milestones panel (3.4) into view and briefly highlights it. In the top strip and with Charts off it toggles a popover under the rail with the same panel content; the popover closes on Escape (focus returns to the tray), on a click outside it, or with its close button, and row clicks keep it open. The tray border turns solid while the popover is open or an unscheduled milestone is the active milestone filter. If no milestone has a due date, the rail shows "No milestones with a due date." next to the tray. Clicking a milestone sets the milestone filter (4.2).

### 3.2 Summary pills

`SummaryBar` (`frontend/src/components/SummaryBar.tsx`), rendered in the left part of the board's toolbar row using counts computed by `buildSummaryGroups` (`frontend/src/lib/summary.ts`) from issues after global scope filters, independent of the board's facets.

| Group | Pill | Count | Board filter |
|---|---|---|---|
| Flow | Open | open issues | open issues |
| | New 7d | issues created in the last 7 days | created in the last 7 days, any state |
| | Closed 7d | issues closed in the last 7 days | closed in the last 7 days |
| Open by priority | P1, P2, ... Unset | open issues per priority, ordered by `priority_rank`, "Unset" last, each with a coloured dot | open issues of that priority |
| Hints | No milestone, Unassigned, Mixed | open issues with that quality signal | that quality signal |

There is no pill for all closed issues; in the Charts layout, clicking a closed stage (such as `Done`) or segment in `Workflow State` selects closed issues.

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
- **Wide desktop (`>= 1360px` in Table view):** two-column split with a `380 px` left analytics rail (`Open Mix` with side-by-side Open Priority and Open Type donuts plus clickable color legends, horizontal stacked `Workflow State` bars across open stages and closed terminal stages with inline priority counts, `Daily New vs. Closed`, and `Issue Quality Signals`, and the `Unscheduled Milestones` panel) beside the full-height `IssuePanel`.
- **Narrower viewports (`< 1360px`) or Kanban Board view:** collapses to a single 4-cell bento strip above `IssuePanel` so the board or table uses full horizontal width.
- **Unscheduled Milestones panel:** `UnscheduledMilestonesChart` lists milestones that have no due date and at least one open issue, sorted by open issue count and then by natural title order. Each row shows the open count and a bar scaled to the largest row. A `Total` / `Priority` / `Type` toggle switches the bar between one segment and open issues stacked by priority or issue type (colours match `Open Mix`; a legend appears in the stacked modes). At most 6 rows are shown, followed by "+k more without a due date"; a selected milestone beyond the cap replaces the last visible row. A footnote counts milestones without a due date whose issues are all closed, which are hidden. Hover shows the open/total counts, the age of the oldest open issue, and the breakdown. Clicking a row sets the global milestone filter, like a timeline marker (4.2). The panel is only rendered when at least one such milestone exists. It sits in the left rail under `Issue Quality Signals` in the wide split only; in the top strip and with Charts off the same content opens as a popover from the release rail tray (3.1), so the strip keeps its four cards.
- **Unified toolbar:** `IssuePanel` displays the issue count and named removable filter chips (`Clear all` when filtered) on the left, with search (`Ctrl/Cmd+K`), Table/Board switch, and `Fit`/10/20/30 paging on the right. `Fit` computes row counts from the panel body height so the table fills the remaining viewport without page scrolling.
- Clicking any chart segment (`PriorityDonut` slice, legend item, or center, `WorkflowStateRow` stage label / priority segment, `DailyVelocityChart` point, or `QualitySignalsChart` bar; `UnscheduledMilestonesChart` rows set the milestone filter instead of `facets`) updates `facets` and sets `activeChart`, dimming sibling elements cleanly. Clicking the active target again or removing its named chip clears the filter while preserving search text.

### 3.5 Count / percent switch

A segmented control next to the Charts toggle in `TopBar` (`#` and `%`, group label "Show numbers as") sets `valueMode` (`"count"` or `"percent"`). It is always visible, because the board lanes use it with Charts off. The choice is kept in `localStorage` (`pulse_value_mode`, default `count`) and is not a URL parameter, so it is not part of the shared-link contract. Percentages are whole numbers from `formatShare` (`frontend/src/lib/analytics.ts`): `<1%` for a nonzero share under 0.5%, `0%` for an empty total.

| Chart | Percent mode shows |
|---|---|
| `Open Mix` donuts | slice labels and legend items as a share of the donut total; the center stays the absolute count |
| `Workflow State` | segment labels as a share of the stage; the right-hand number as the stage's share of the issues in all rows above the divider (closed-only rows below it: of all closed-only rows); bar geometry is unchanged |
| `Issue Quality Signals` | the right-hand number as a share of open issues |
| `Unscheduled Milestones` | the right-hand number as a share of all open issues in unscheduled milestones; legend items as the same share |
| Board lane priority pills | the priority's share of the lane's issues; the lane title keeps the count |
| `DailyVelocityChart` | unchanged |

Tooltips show both the count and the share in either mode (the release rail tooltip always shows "Issues: closed/total closed (share)").

## 4. Interactions

### 4.1 Board filter

The board is always visible and shows all open issues until something filters it. Its filter is a set of facets (`stage`, `state`, `priority`, `issue_type`, `signal`, `recent`, `day` with `day_kind`, `query`) in `frontend/src/lib/facets.ts`:

- a summary pill sets the base facets (3.2),
- a lane pill adds `stage` and `priority` (3.3),
- a chart click in the Analytics layout sets the facets the segment stands for: an `Open Mix` slice or legend item sets open `state` with its `priority` or `issue_type` (and the donut center selects all open issues), a workflow-state bar sets its stage, bucket state (`opened`, `closed`, or `all`), and priority, a velocity point sets the day and `created` (`state: "all"`) or `closed` (`state: "closed"`), and a quality bar sets the signal on open issues (3.4),
- the search field in the board's toolbar sets `query` (4.5).

Open issues are the default: a missing `state` means `opened`, and only `closed` or `all` is shown as a chip (not next to a 7-day filter, which already says which issues it covers).

While the board is filtered, a row under the toolbar shows one removable chip per facet and per active global scope filter (team, context, milestone, time range), "Clear all" and the issue count.

### 4.1.1 URL state

The facets, the picked summary pill, and active global scope filters are mirrored into query parameters (`summary`, `f_stage`, `f_state`, `f_priority`, `f_issue_type`, `f_signal`, `f_recent`, `f_day`, `f_day_kind`, `f_query`, `g_team`, `g_context`, `g_milestone`, `g_preset`, `g_start`, `g_end`; the layout uses `view`), so a refresh or a shared link restores the same workspace view. Malformed values are ignored.

### 4.2 Milestone synchronization

The release timeline and milestone scope filter are synchronized bidirectionally through session and URL state. Selecting a milestone from the timeline updates the milestone token in `ScopeBar` (`g_milestone`), and clearing it via the token/toolbar chip resets timeline selection state.

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
