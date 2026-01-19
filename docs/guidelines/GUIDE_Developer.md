# **Developer Guidelines: GitLabInsight**

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

### **3.3. Singleton / Memoization (Layer 3\)**

Used for **Data Loading**.

* **Implementation:** Streamlit's @st.cache\_data acts as a Singleton provider for the DataFrames. It ensures we only parse the Parquet files once per TTL window, regardless of how many users view the app.

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

## **9. Streamlit Configuration**

### **9.1. Network Access (Local Development)**

When running the dashboard on one machine and accessing it from another (e.g., via `http://192.168.x.x:8501`), you may encounter:

```
TypeError: Failed to fetch dynamically imported module: http://<IP>:8501/static/js/index.*.js
```

**Root Cause:** By default, Streamlit binds to `localhost`, so when the browser fetches JavaScript/CSS assets from an external IP, the requests fail.

**Solution:** Configure `.streamlit/config.toml`:

```toml
[server]
headless = true
# Bind to all interfaces so the app is accessible from other machines
address = "0.0.0.0"
# Disable CORS and XSRF protection for local network access during development
enableCORS = false
enableXsrfProtection = false
```

> ⚠️ **Production Warning:** `enableCORS = false` is acceptable for local development but **should not be used in production**. For production deployments, use a reverse proxy (nginx, Caddy, Traefik) that handles CORS properly.

### **9.2. Timezone-Aware Date Arithmetic**

When performing date arithmetic with Pandas timestamps, ensure timezone consistency:

```python
# BAD - Mixing tz-naive and tz-aware raises TypeError
remaining = (due_date - pd.Timestamp.now()).days

# GOOD - Both timestamps are tz-aware (UTC)
remaining = (due_date - pd.Timestamp.now(tz="UTC")).days
```

**Why:** GitLab API returns ISO 8601 timestamps with timezone info (UTC). When parsed by Pandas, these become tz-aware. Subtracting a tz-naive `pd.Timestamp.now()` from a tz-aware timestamp raises `TypeError: Cannot subtract tz-naive and tz-aware datetime-like objects`.
