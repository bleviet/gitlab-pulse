# **Operations Guide: GitLab Pulse**

Version: 1.0  
Scope: Routine maintenance, data updates, and configuration management.

## **1. Data Update Lifecycle**

The system follows a linear pipeline (Medallion Architecture). Steps must be executed in order for changes to propagate.

### **1.1. Pipeline Overview**

| Stage | Component | Action | Command | Frequency |
| :--- | :--- | :--- | :--- | :--- |
| **L1** | **Collector** | Fetches new data from GitLab API | `uv run python app/collector/orchestrator.py` | Daily / Hourly |
| **L2** | **Processor** | Applies rules & validation Logic | `uv run python app/processor/main.py` | After L1 |
| **L3** | **Dashboard** | Serves API & React SPA over processed data | `uv run python -m app.dashboard` | Continuous |

---

## **2. FAQ: Common Operational Tasks**

### **Q: How and when will the data be updated?**
**A:** Data is updated **manually** or via **external scheduler** (e.g., cron, CI/CD pipeline). The system does not self-update in the background.
- **Standard Schedule:** We recommend running the L1 Collector and L2 Processor nightly.
- **Incremental Sync:** The collector automatically uses `updated_after` to fetch only new changes since the last run.

### **Q: When will the processor be executed?**
**A:** The processor should be executed **immediately after the collector finishes**.
- It transforms the raw JSON/Parquet (L1) into enriched Analytics Parquet (L2).
- If you run the Collector but skip the Processor, the Dashboard will continue showing old data.

### **Q: When does the dashboard reflect newly processed data?**
**A:** On the very next request after Parquet or YAML files change on disk.
- **Automatic Mtime Check:** `DashboardService` tracks modification timestamps (`st_mtime_ns`) on `issues_valid.parquet`, `labels_*.parquet`, `sync_state.json`, and `app/config/rules/*.yaml`, rebuilding its in-memory payload automatically when files change.
- **Manual Refresh:** Click the ambient refresh button (status dot + arrows icon) in the top-right navigation bar to reload `/api/dashboard` immediately without reloading the browser page.

### **Q: I updated `default.yaml`. How do I see the changes?**
**A:** Color overrides under `colors.light` / `colors.dark` are resolved at read time via `DashboardService` mtime detection. Changes to classification rules, workflow stages, or quality rules take effect during **Layer 2 Processing**:
1. **Edit:** Modify `app/config/rules/default.yaml`.
2. **Apply:** Run the Processor:
   ```bash
   uv run python app/processor/main.py
   ```
3. **View:** Click the top-right refresh button (or open **Ops** -> **Clear Cache & Reload**).

---

## **3. Admin Interface (UI-based Operations)**

For operators who prefer a graphical interface, the Dashboard includes a password-protected **Admin Operations** modal.

### **3.1. Accessing the Admin Panel**
1. Click **Ops** (or **Admin**) in the top-right navigation bar.
2. Enter the password (default: `admin`, or set via `ADMIN_PASSWORD` env var).

### **3.2. Available Actions**
| Action | Description |
| :--- | :--- |
| **Run Collector (L1)** | Trigger data fetch from GitLab directly from UI |
| **Run Processor (L2)** | Trigger data processing directly from UI |
| **Clear Cache** | Force immediate refresh of dashboard data |

---

## **4. Project Auto-Discovery**

After the initial setup, the Collector can automatically determine which projects to sync.

### **4.1. First-Time Setup**
You must specify `PROJECT_IDS` for the first sync. Copy the environment template and fill in your values:
```bash
cp .env.example .env
# Edit .env: set GITLAB_URL, GITLAB_TOKEN, and PROJECT_IDS
uv run python app/collector/orchestrator.py
```

### **4.2. Subsequent Syncs**
Once projects are in `sync_state.json`, you can remove `PROJECT_IDS` from `.env`. The Collector will:
1. Read `data/state/sync_state.json`.
2. Re-sync all previously tracked projects.

This means the Admin "Run Collector" button works without any manual configuration.

---

## **5. Milestones**

The Collector also fetches **milestones** independently from issues.

- **Storage:** `data/processed/milestones_{project_id}.parquet`
- **Sync Behavior:** Always full refresh (lightweight, no incremental needed)
- **Dashboard:** Milestone data remains available for downstream analytics and future dashboard extensions.

---

## **6. Automation Example (Cron)**

To automate this daily at 2 AM:

```bash
0 2 * * * cd /path/to/repo && uv run python app/collector/orchestrator.py --full-sync >> logs/cron.log 2>&1
30 2 * * * cd /path/to/repo && uv run python app/processor/main.py >> logs/cron.log 2>&1
```
