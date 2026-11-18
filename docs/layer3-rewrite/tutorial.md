# Tutorial: First Run With the FastAPI + React Dashboard

This walkthrough takes you from a fresh checkout of branch `feat/fastapi-react-dashboard` to running the dashboard locally on synthetic data and exercising Analytics view, Compact view, search, filters, and Admin Operations.

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

## 4. Explore the Default Analytics View

The dashboard opens in **Analytics** (selected on the left side of the top-right `Analytics | Compact` switch):

1. **Release Timeline (top left):** Hover over any milestone pin to inspect its due date, closed/total issue count, and status (`Complete`, `Incomplete`, `On Track`, `Overdue`, or `Unscheduled`). Click a pin to filter the entire dashboard to that milestone; click the same pin again to clear the milestone filter.
2. **Closed & Open Priority Donuts:** Click any priority slice (for example `P1`) to filter the issue list below to that state and priority. Click the center total (`OPEN ISSUES` or `CLOSED ISSUES`) to select all issues in that state.
3. **Issue Quality Signals & Daily Velocity:** Click a bar in `Issue Quality Signals` (such as `Missing Milestone`) or a day point in `Daily New vs. Closed Issues` to filter the panel below. Notice the sibling elements dim and a `Chart filter active` chip appears above the table.
4. **Issues by Workflow State:** Click a vertical bar under any stage column (such as `Review`). Only that stage and priority bar remain full opacity, and the issue table/board below filters immediately without a page reload.

## 5. Switch to Compact View for Daily Triage

Click **Compact** on the right side of the top-right layout switch. Notice the URL updates to `?view=compact` while carrying over any active filters.

1. **Summary Pills:** Use the `Flow` (`Open`, `New 7d`, `Closed 7d`), `Open by priority`, and `Hints` pills on the left of the toolbar to jump between common triage slices.
2. **Inline Search (`Ctrl/Cmd+K`):** Press `Ctrl+K` (or `Cmd+K` on macOS). The search pill widens in place. Type a partial query across title, assignee, milestone, priority, or stage—if an exact multi-word match returns nothing, typo-tolerant fuzzy matching kicks in automatically. Press `Escape` to leave the search field.
3. **Table and Board Switching:**
   - In **Table** view, `Fit` sizing fills the available viewport height (use `10`, `20`, or `30` for fixed pages). Click column headers to sort or leave unsorted to view parent-child hierarchy indentation.
   - Click **Board** in the toolbar to switch to the Kanban lanes. Sticky lane headers display a stacked priority bar and clickable priority pills. Scroll horizontally on narrow screens—the lane headers remain aligned with the lanes below.

## 6. Use Filters, Themes, and Admin Operations

1. Click **Filters** at the top-left of the navigation bar to open the collapsible drawer. Filter by `Domain / Team`, `Context / Sub-Project`, `Milestone`, or `Time Range` (`30 Days`, `90 Days`, `1 Year`, `All Time`). A badge on the `Filters` button shows how many drawer filters are active after you close it.
2. Click the sun/moon icon in the top-right bar to switch between dark mode (default) and light mode; the preference is saved in `localStorage` without reloading the page.
3. Click **Ops** in the top-right bar, authenticate with your `ADMIN_PASSWORD` (default `admin`), and click **Run Processor (L2)** or **Clear Cache & Reload** to rebuild analytics and refresh the browser payload in place.
