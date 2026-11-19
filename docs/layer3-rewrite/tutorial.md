# Tutorial: First Run With the FastAPI + React Dashboard

This walkthrough takes you from a fresh checkout of branch `feat/fastapi-react-dashboard` to running the dashboard locally on synthetic data and exercising Charts on/off modes, tokenized scope search, inline issue search, and Admin Operations.

## Prerequisites

- Python `>= 3.11` and `uv`
- Node.js `>= 20` and `npm`

## 1. Install Dependencies and Build the Frontend

From the repository root, install Python dependencies, build the React/TypeScript SPA, and confirm the unit tests pass:

```bash
uv sync
cd frontend && npm ci && npm run build && cd ..
```

## 2. Generate and Process Synthetic Data

Create 1,000 local synthetic issues (including sample quality errors) and run the Layer 2 processor to produce `data/analytics/issues_valid.parquet`:

```bash
uv run python tools/seeder.py --count 1000 --inject-errors
uv run python app/processor/main.py
```

## 3. Launch the Dashboard

Start the FastAPI server:

```bash
uv run python -m app.dashboard
```

Open `http://127.0.0.1:8501` in your browser.

## 4. Explore the Default Workspace With Charts On

The dashboard opens in a single-viewport cockpit with the **Charts** toggle active in the top-right bar and the slim **Release Timeline** pinned at the top:

1. **Release Timeline (top strip):** Hover over any milestone pin to inspect its due date, closed/total issue count, and status (`Complete`, `Incomplete`, `On Track`, `Overdue`, or `Unscheduled`). Click a pin to filter the entire dashboard to that milestone; click the same pin again (or click its chip in the toolbar) to clear it.
2. **Open Mix (Priority & Issue Type Donuts):** Click any slice or legend item in `OPEN PRIORITY` or `OPEN BY TYPE` (for example `P1` or `Bug`) to filter the issue list to open issues matching that priority or type. Click either center total to select all open issues.
3. **Workflow State:** Click a horizontal priority segment—or a stage name—for any active open stage or closed terminal stage (`Done`) to filter the issue table/board immediately without a page reload.
4. **Daily New vs. Closed & Issue Quality Signals:** Click a day point in `Daily New vs. Closed` (`New` includes all issues created that day; `Closed` filters closed issues) or a bar in `Issue Quality Signals` (`Open Hints`, such as `Missing Milestone`) to filter the issue panel. Sibling elements dim and named filter chips (such as `Signal: Missing Milestone`) appear directly in the issue toolbar.

## 5. Toggle Charts Off for High-Density Triage

Click **Charts** in the top-right bar to toggle the four analytics cards off. Notice the URL updates to `?view=compact` while keeping the slim Release Rail at the top and carrying over all active filter chips.

1. **Summary Pills:** When Charts are off, the `Flow` (`Open`, `New 7d`, `Closed 7d`), `Open by priority`, and `Hints` pills appear automatically above the issue toolbar for 1-click triage filtering.
2. **Inline Search (`Ctrl/Cmd+K`):** Press `Ctrl+K` (or `Cmd+K` on macOS). The search pill widens in place. Type a partial query across title, assignee, milestone, priority, or stage—if an exact multi-word match returns nothing, typo-tolerant fuzzy matching kicks in automatically. Press `Escape` to leave the search field.
3. **Table and Board Switching:**
   - In **Table** view, `Fit` sizing automatically fills the expanded height (use `10`, `20`, or `30` for fixed pages). Click column headers to sort or leave unsorted to view parent-child hierarchy indentation.
   - Click **Board** in the toolbar to switch to the Kanban lanes. Sticky lane headers display a stacked priority bar and clickable priority pills. Scroll horizontally on narrow screens—the lane headers remain aligned with the lanes below.

## 6. Use Global Scope Search, Time Presets, Themes, and Admin Operations

1. Use the unified scope input centered in the top bar to filter by `Context`, `Milestone`, or `Team` (when multiple teams exist). Type multi-term fuzzy queries like `proj v14` to see `Quick apply` pairs (`project::A + v1.4`), or pick individual suggestions; each selection appears as a removable token. Beside it, pick `30d`, `90d`, `1y`, `All`, or click the calendar button for custom dates, and click the status-dot refresh button next to `Charts` to check or reload data.
2. Click the sun/moon icon in the top-right bar to switch between dark mode (default) and light mode; the preference is saved in `localStorage` without reloading the page.
3. Click **Ops** in the top-right bar, authenticate with your `ADMIN_PASSWORD` (default `admin`), and click **Run Processor (L2)** or **Clear Cache & Reload** to rebuild analytics and refresh the browser payload in place.
