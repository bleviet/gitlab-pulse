# **Operations Guide: GitLabInsight**

Version: 1.0  
Scope: Routine maintenance, data updates, and configuration management.

## **1. Data Update Lifecycle**

The system follows a linear pipeline (Medallion Architecture). Steps must be executed in order for changes to propagate.

### **1.1. Pipeline Overview**

| Stage | Component | Action | Command | Frequency |
| :--- | :--- | :--- | :--- | :--- |
| **L1** | **Collector** | Fetches new data from GitLab API | `uv run python app/collector/orchestrator.py` | Daily / Hourly |
| **L2** | **Processor** | Applies rules & validation Logic | `uv run python app/processor/main.py` | After L1 |
| **L3** | **Dashboard** | Visualizes processed data | `uv run streamlit run app/dashboard/main.py` | Continuous |

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

### **Q: Will the Streamlit visual be updated?**
**A:** Yes, but with a delay.
- **Cache TTL:** The Dashboard caches data in memory for **15 minutes** (900 seconds).
- **Auto-Refresh:** If you leave the dashboard open, it will reload data from disk every 15 minutes.
- **Manual Refresh:** To see changes immediately after running the Processor:
  1. Go to the Dashboard.
  2. Press `C` (Clear Cache) or click **Wait for it...** > **Clear Cache** in the menu.
  3. Refresh the browser page.

### **Q: I updated `default.yaml`. How do I see the changes?**
**A:** Configuration changes (e.g., new label mappings, color changes) are applied during **Layer 2 Processing**.
1. **Edit:** Modify `app/config/rules/default.yaml`.
2. **Apply:** Run the Processor:
   ```bash
   uv run python app/processor/main.py
   ```
3. **View:** Refresh the Dashboard (and clear cache).

---

## **3. Automation Example (Cron)**

To automate this daily at 2 AM:

```bash
0 2 * * * cd /path/to/repo && uv run python app/collector/orchestrator.py --full-sync >> logs/cron.log 2>&1
30 2 * * * cd /path/to/repo && uv run python app/processor/main.py >> logs/cron.log 2>&1
```
