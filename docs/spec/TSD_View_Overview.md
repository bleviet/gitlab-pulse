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

## 3. Layouts

The Overview has two layouts that share one issue board, one filter (4.1) and one URL format. A "Compact | Analytics" switch at the top right of the page changes the layout. It is pinned into Streamlit's header bar, so it takes no height and stays in place while the page scrolls. The choice is kept in the session and in the URL (`?view=analytics`). The filter carries over when switching.

| Layout | Purpose | Above the board |
|---|---|---|
| Compact (default) | Daily triage: as many cards on screen as possible | A thin release rail; the summary pills share the board's toolbar row (3.1 to 3.3) |
| Analytics | Stepping back: trends, review meetings, reports | The original chart grid (3.4) |

### 3.0 Compact layout

One column, one focus: the issue board, which starts high on the screen (on a 13-inch MacBook the first cards start at about 40 % of the window height). Nothing competes with the board for width or height, so the page works the same on a 13-inch laptop and on a 34-inch ultrawide screen.

| Row | Content |
|---|---|
| Releases | The milestone timeline as a thin rail with its label inside (3.1) |
| Board toolbar | Summary pills on the left (3.2); search (⌘K) and the Board/Table switch on the right |
| Filter chips | Only while the board is filtered: one chip per filter, "Clear all", the issue count |
| Lanes | The board; the workflow state is shown in its lane headers (3.3) |

- The page switch (Overview, Custom View, Admin) is in the sidebar, and Streamlit runs with `toolbarMode = "minimal"` (no "Deploy" button), so the page has no navigation row of its own.
- The sidebar is collapsed by default; its filters are also available in the search panel (4.5) and shown as chips on the board.
- On a narrow window the lanes keep a minimum width of 15rem and the board scrolls sideways, instead of squeezing the cards.
- Lane height follows the window height (between 320 and 1000 px). A lane wider than two cards (large screens) shows its cards in several columns.

### 3.1 Release rail

`milestone_timeline` with `style="rail"`: a soft band with a centre rail, round markers coloured by status (complete, incomplete, on track, overdue) that alternate above and below the rail in date order, their names next to them, and a pink line labelled "NOW" for today. Clicking a milestone sets the milestone filter (4.2).

### 3.2 Summary pills

`render_summary_bar` in `app/dashboard/views/overview_summary.py`, rendered in the left part of the board's toolbar row. The groups are separated by a thin rule; on narrow windows the pills wrap while search and the view switch stay at the top right. The counts are computed by `build_summary` from the issues after the sidebar filters, independent of the board's filters.

| Group | Pill | Count | Board filter |
|---|---|---|---|
| Flow | Open | open issues | open issues |
| | New 7d | issues created in the last 7 days | created in the last 7 days, any state |
| | Closed 7d | issues closed in the last 7 days | closed in the last 7 days |
| Open by priority | P1, P2, ... Unset | open issues per priority, ordered by `priority_rank`, "Unset" last, each with a coloured dot | open issues of that priority |
| Hints | No milestone, Unassigned, Mixed | open issues with that quality signal | that quality signal |

There is no pill for all closed issues; the search panel's Open/Closed/All switch covers it.

Picking a pill replaces the board's filter (the search text is kept) and shows the pill as picked; picking it again resets the board to all open issues. The pills are native `st.pills`; the picked pill uses the accent colour.

### 3.3 Lane headers

The workflow-state chart was a separate row above the board; its columns had to be kept aligned with the lanes. It is now part of each lane header (`lane_header` option of the board widget):

- the stage name and the number of cards in the lane,
- a thin stacked bar of the lane's issues by priority,
- one compact pill per priority: a coloured dot and the count. The dot colours follow `priority_rank` (`priority_color_names`) and are the same as on the summary's priority pills.

Every lane header has these three rows, so the lanes stay aligned whatever the stage names.

The header counts ignore the stage and priority filters, so every lane keeps its full priority mix. Picking a lane pill refines the current filter with that stage and priority (and open issues, unless a state is set); picking it again removes the refinement.

### 3.4 Analytics layout

`render_analytics_layout` in `app/dashboard/views/overview_analytics.py`: three rows of panels, based on the original chart grid, then the board.

| Row | Panels |
|---|---|
| 1 | Release Timeline (three quarters of the width), Closed Issues by Priority (donut) |
| 2 | Open Issues by Priority (donut), Issue Quality Signals, Daily New vs. Closed Issues (7 days) |
| 3 | Issues by Workflow State (priority bars per stage); stays pinned below the header while the board scrolls |

The quality signals count open issues only, so they sit next to the open-issues donut. The workflow-state row and the board share a container, so the row is released where the board ends; its stage columns line up with the board's lanes. The original "Open vs. Closed Issues" panel is gone: a click in a donut's centre selects all open (or all closed) issues, and the donuts already show both totals.

The donuts are drawn on x/y axes instead of as Plotly pies, because Plotly reports no click selection for pie (or polar bar) slices. Each slice is a filled ring segment; a grid of invisible markers over the ring and one large marker over the hole are the click targets, carrying `[priority, count]` (the centre: `__all__`) in `customdata`. Since the click targets are invisible, the donut draws its own highlight: while its filter is active, the other slices are dimmed (`highlight` option, from `chart_priority_highlight`).

A click on a chart segment filters the board below the grid (it does not open a dialog) and the segment stays highlighted by Plotly's own selection (the donuts draw theirs, see above). When the filter changes another way (a chip, a pill, "Clear all", the search panel), the charts are rebuilt with new widget keys so the highlight disappears. In this layout the board's toolbar shows an "Issues" label instead of the summary pills, since the charts show the same counts.

## 4. Interactions

### 4.1 Board filter

The board is always visible and shows all open issues until something filters it. Its filter is a set of facets (`stage`, `state`, `priority`, `signal`, `recent`, `day` with `day_kind`, `query`) in `app/dashboard/views/issue_data.py`:

- a summary pill sets the base facets (3.2),
- a lane pill adds `stage` and `priority` (3.3),
- a chart click in the Analytics layout sets the facets the segment stands for (`facets_from_selection`): a donut slice its state and priority, a donut centre its state, a workflow-state bar its stage, open state and priority, a velocity point the day and created/closed, an open/closed bar the state, a quality bar the signal (3.4),
- the search panel sets `query`, `state` and the sidebar filters (4.5).

Open issues are the default: a missing `state` means `opened`, and only `closed` or `all` is shown as a chip (not next to a 7-day filter, which already says which issues it covers).

While the board is filtered, a row under the toolbar shows one removable chip per facet and per active sidebar filter (team, context, milestone, time range), "Clear all" and the issue count.

### 4.1.1 URL state

The facets, the picked summary pill and the selected issue are mirrored into query parameters (`summary`, `f_stage`, `f_state`, `f_priority`, `f_signal`, `f_recent`, `f_day`, `f_day_kind`, `f_query`, `issue_project_id`, `issue_iid`; the layout uses `view`), so a refresh or a shared link restores the same view. The URL is only read when it differs from what the session last wrote, which is the case on page load. Malformed values are ignored. Sidebar filters are not part of the URL.

### 4.2 Milestone synchronization

The release timeline and sidebar milestone selector are synchronized bidirectionally through session state. Selecting a milestone from the timeline updates the sidebar filter, and clearing the sidebar resets timeline selection state.

### 4.3 Issue board

The board (`app/dashboard/views/issue_panel.py`) shows Board by default; the choice between Board and Table is kept in `filtered_issues_view` in session state. The search text from the search panel (4.5) applies to both views.

**Board.** Lanes are the stages that have open issues, in workflow order (`overview_stages`). Lanes without matching issues stay visible and empty. Other stages (for example "Done" for closed issues) are appended; when none of the issues is in one of those stages, only the stages with issues are shown, in the same column width. The board ignores the `stage` facet and marks that stage's lane instead, so the other stages stay visible for comparison; the caption shows the total and the count in the marked stage. Each lane shows at most 50 cards and scrolls on its own.

**Table.** The table applies all facets. It shows one row per issue (several contexts appear as chips in the Context column), sorted by priority rank and then by days in stage. The Stage column is hidden while a stage facet is active, and the Quality hints column is shown only when a listed issue has hints.

**Issue detail.** Selecting a card or a row opens the issue in place of the board or table, next to a column of cards. From the board, that column is the lane the issue was opened from; from the table, it is the table order. The open card is outlined and scrolled into view. Previous/next follow that column. "Back to board" or "Back to table" returns to the list.

The recently viewed issues are listed in the search panel (4.5).

Issue state changes are not possible from the list; they are made in GitLab.

### 4.4 Local seeded issue details

For locally seeded issues, the detail flow resolves from local parquet-backed data rather than assuming a live GitLab API lookup. This keeps local demo workflows usable end-to-end.

### 4.5 Search panel (Ctrl/Cmd+K)

Ctrl+K (⌘K on macOS), or the search button in the board header, opens a floating search panel (`st.dialog`). The shortcut is a small keyboard listener added to the page that clicks the search button.

- The search box has focus when the panel opens. While it is empty, the panel lists the last five issues opened in the session ("Recently viewed"). Results update as you type: the top eight matching issues, by priority and then time in stage. Selecting one closes the panel and opens the issue on the board.
- Quick filter: Open, Closed or All issues.
- The active board facets (except search and state, which have their own controls) are shown as removable chips.
- The sidebar filters (domain/team, context, milestone, time range) are repeated here and stay in sync with the sidebar.
- Esc, the close button or a click outside closes the panel. The search text stays applied to the board as a "Search" chip.

The search box is the `st_keyup` component, which renders in an iframe. Keys typed there do not reach the page, so the listener forwards Esc from the iframe to close the panel.

## 5. Notes on Scope

- The active top-level page name is **Overview**
- Overview is intentionally curated; it is not the same surface as the generic custom layout builder
