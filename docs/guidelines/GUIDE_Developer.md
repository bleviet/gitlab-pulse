# **Developer Guidelines: GitLab Pulse**

Version: 1.0  
Scope: Coding standards, design patterns, and architectural principles for maintainable implementation.

## **1\. Core Philosophy**

### **1.1. The "Pit of Success"**

Our architecture is designed so that doing the *right* thing is easier than doing the *wrong* thing.

* **Wrong:** Manually parsing JSON dates.  
* **Right:** Defining a Pydantic model where created\_at: datetime handles it automatically.

### **1.2. The Layered Boundary Rule**

Dependencies point **inwards** (or downwards).

* **Layer 3 (UI)** depends on **Layer 2 (Analytics)** data.  
* **Layer 2 (Logic)** depends on **Layer 1 (Processed)** data.  
* **Layer 1** depends on **Layer 0 (Raw)** data.  
* **Strict Rule:** Layer 1 must *never* import business logic from Layer 2\. The Collector should not know what a "Stale Bug" is.

## **2\. Python Implementation Standards**

### **2.1. Type Safety (mypy)**

We use **Strict Typing**. Any is forbidden in core logic.

* **Why:** We deal with massive datasets. Type errors in data pipelines usually manifest as silent data corruption, which is expensive to fix.  
* **Standard:**  
  \# BAD  
  def process(data): ...

  \# GOOD  
  def process(data: List\[RawIssue\]) \-\> pd.DataFrame: ...

### **2.2. Pydantic Best Practices**

Use **Pydantic V2** for all data transfer objects (DTOs).

* **Validation:** Use @field\_validator for single fields and @model\_validator(mode='after') for cross-field logic (e.g., "If Task, Parent ID is required").  
* **Immutability:** Prefer frozen=True for configuration models to prevent runtime side-effects.

### **2.3. Pandas & Vectorization (Performance)**

We process 100k+ rows. Python loops are too slow.

* **Rule:** Never use df.iterrows() or for loops over DataFrames.  
* **Pattern:** Use Vectorized Operations.  
  \# BAD (O(n))  
  for index, row in df.iterrows():  
      df.at\[index, 'age'\] \= (now \- row\['created\_at'\]).days

  \# GOOD (Vectorized \- C Speed)  
  df\['age'\] \= (now \- df\['created\_at'\]).dt.days

* **Memory:** Use category dtype for low-cardinality string columns (e.g., project\_id, state) to save 90% RAM.

## **3\. Design Patterns in Use**

### **3.1. Strategy Pattern (Layer 1\)**

Used in the **Hybrid Collector**.

* **Context:** DataAcquisitionService.  
* **Strategies:** RestStrategy (Metadata) and GqlStrategy (Hierarchy).  
* **Usage:** The service swaps strategies depending on the data need, keeping the main loop clean.

### **3.2. Factory Pattern (Layer 2\)**

Used for **Data Validation**.

* **Problem:** We have raw dicts and need either a ValidIssue or a QualityIssue.  
* **Implementation:** A ValidationFactory takes a raw row and the DomainConfig, applies the rules, and returns the correct object type. This encapsulates the complex "if/else" logic of the business rules.

### **3.3. Caching & Payload Preparation (Layer 3)**

Used for **Data Loading** in `DashboardService` (`app/dashboard/service.py`).

* **Implementation:** `DashboardService` acts as an mtime-keyed cache over `issues_valid.parquet`, `labels_*.parquet`, `sync_state.json`, and the active rule files (`data/rules/*.yaml`, or `app/config/rules/*.yaml` until the first save from the dashboard rule editor). It collapses multi-context rows into unique issues and resolves YAML palettes once per file modification timestamp (`st_mtime_ns`), with explicit invalidation via `clear_cache()`.

## **4\. Extensibility & OCP (Open/Closed Principle)**

**Goal:** Add new functionality without modifying existing code.

### **4.1. Adding New Metrics**

Do not modify the RawIssue class.

* **Mechanism:** Add a new **Enricher Function** in Layer 2\.  
* **Example:** To add "Time in Review", create enrich\_review\_time(df) and register it in the processing pipeline.

### **4.2. Adding New Teams**

Do not edit main.py.

* **Mechanism:** Create a new rules/team\_x.yaml.  
* **Logic:** The RuleLoader dynamically discovers the new file. The system is "Open for extension" (new YAMLs) but "Closed for modification" (core loader logic).

## **5\. DRY (Don't Repeat Yourself)**

### **5.1. Shared Schemas**

* **Problem:** Layer 1 writes Parquet, Layer 2 reads it.  
* **Solution:** Define the Schema **once** in app/shared/schemas.py (or collector/models.py). Both the Writer and Reader must import this definition.

### **5.2. Date Handling**

* **Rule:** Dates are hard. Use a single utility parse\_iso\_datetime throughout the app. Do not implement strptime in multiple places. Consistency in Timezone handling (always UTC) is critical.

## **6\. Testing Strategy**

### **6.1. Unit Tests (Logic)**

* Focus on **Layer 2 Validators**.  
* **Pattern:** Create "Fixture Issues" (e.g., a perfect bug, a buggy bug) and assert that the Validator sorts them correctly.

### **6.2. Integration Tests (Seeder)**

* Use the seeder.py tool.  
* **Requirement:** Before opening a PR, run the seeder with 10k issues and verify that the Dashboard loads in \< 2 seconds.

## **7\. Error Handling & Resilience**

### **7.1. Fail Gracefully**

* **Layer 1:** If one project fails to sync (e.g., 403 Forbidden), log the error and **continue** to the next project. Do not crash the entire cron job.  
* **Layer 2:** If a rules.yaml file is malformed, skip that specific team and log an error. The rest of the dashboard must remain operational.

### **7.2. Atomic Operations**

* **File I/O:** Always write to a temporary file (.tmp) and rename (os.replace) to the final destination. This prevents corrupt Parquet files if the process is killed mid-write.

## **8. Coding Style & Consistency**

### **8.1. Match Existing Style**
* **Rule:** When modifying existing files, always mimic the coding style of the surrounding code.
* **Why:** Consistent codebases are easier to read and maintain. If the file uses `type: ignore` comments, follow that pattern. If it uses specific variable naming conventions, adopt them.
* **Review:** Changes that introduce inconsistent styling (e.g., using camelCase in a snake_case file) will be rejected.

## **9. Layer 3 Configuration & Theming (FastAPI + React/TypeScript)**

### **9.1. Network Access (Local Development)**

By default, `uv run python -m app.dashboard` binds to `127.0.0.1:8501`. When exposing the server on a local network interface during development, pass `--host`:

```bash
uv run python -m app.dashboard --host 0.0.0.0 --port 8501
```

For hot-reload frontend development, run `uv run python -m app.dashboard --reload` on `:8501` alongside `cd frontend && npm run dev` on `:5173` (which proxies `/api/*` to `http://127.0.0.1:8501`). Put TLS termination and access controls in a reverse proxy (nginx, Caddy, Traefik) for shared deployments.

### **9.2. CSS Tokens & Semantic Colors (Required)**

UI chrome and data colors follow the `brand-guidelines` and `frontend-design` skills:

* **UI Chrome Tokens:** Declared in `frontend/src/styles/tokens.css` under `:root` (dark default), `[data-theme="light"]`, and per-user `[data-color-theme="<id>"]` overrides paired with `frontend/src/lib/uiThemes.ts`. Do not hardcode hex values for backgrounds, text, borders, or surfaces inside components.
* **Semantic Data Palettes:** Defined in `app/dashboard/palettes.py` (`_SEMANTIC_DARK` / `_SEMANTIC_LIGHT`), merged with `colors.light` / `colors.dark` overrides from the team rule YAML, and resolved on the client via `frontend/src/lib/colors.ts` (with per-user overlays when a non-default personal theme is active).
* **Self-Hosted Fonts:** `Manrope`, `Space Grotesk`, and `Space Mono` are stored in `frontend/public/static/` and loaded via `frontend/src/styles/fonts.css` with zero external requests.

### **9.3. Timezone-Aware Date Arithmetic**

When performing date arithmetic with Pandas timestamps, ensure timezone consistency:

```python
# BAD - Mixing tz-naive and tz-aware raises TypeError
remaining = (due_date - pd.Timestamp.now()).days

# BETTER - But assumes due_date is always tz-aware
remaining = (due_date - pd.Timestamp.now(tz="UTC")).days

# BEST - Handle both tz-aware and tz-naive dates
due_date = pd.to_datetime(raw_date)
if due_date.tz is None:
    due_date = due_date.tz_localize("UTC")
now = pd.Timestamp.now(tz="UTC")
remaining = (due_date - now).days
```

**Why:** Different GitLab instances return dates in different formats:
- **Self-hosted GitLab**: Often returns tz-aware dates (UTC)
- **GitLab.com**: May return tz-naive dates

Always normalize dates to UTC before performing arithmetic to handle both cases.
