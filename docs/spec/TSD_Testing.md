# **Technical Specification: Testing & Performance Strategy**

Version: 1.0  
Scope: Validation of system logic (Layer 2\) and performance (Layer 3\) using synthetic data, effectively decoupling testing from the live GitLab API.

## **1\. Strategy Overview**

### **1.1. The "Bypass" Pattern**

Since Layer 1 (Collector) depends on external API availability and rate limits, strict performance testing cannot rely on it. Instead, we implement a **Layer 1 Bypass**: a Data Seeder that generates Parquet files directly into data/processed/.

| Component | Test Method | Tool |
| :---- | :---- | :---- |
| **Layer 1** | Unit Tests with API Mocking | pytest, respx |
| **Layer 2** | Logic Verification via Seeding | tools/seeder.py |
| **Layer 3** | Load Testing via Seeding | Streamlit Profiler |

## **2\. Component: Synthetic Data Generator (The Seeder)**

Location: tools/seeder.py  
Goal: Generate 100,000+ realistic issue records in \< 5 seconds to stress-test the Analytics Engine.

### **2.1. Generation Logic Specification**

#### **A. Temporal Distribution (Realistic Aging)**

* **Creation:** Distribute creation dates randomly over N years.  
* **Closure:** Do not use uniform distribution. Use **Exponential Distribution** for time\_to\_close.  
  * *Why:* Real projects have many "quick fixes" (1-3 days) and few "long-term bugs" (100+ days). Uniform random noise does not test the "Aging Boxplots" effectively.  
* **Staleness:** Ensure 10-15% of open issues have updated\_at \< (now \- 30 days) to verify the "Stale Issue" logic in Layer 2\.

#### **B. Error Injection (Quality Testing)**

To verify Layer 2's validation engine, the seeder must probabilistically inject "dirty data":

* **Missing Labels (5%):** Create issues with no type:: label.  
* **Conflicts (1%):** Create issues with both type::bug and type::feature.  
* **Zombie Tasks (2%):** Create Tasks (work\_item\_type='TASK') where parent\_id refers to a non-existent ID.

### **2.2. Output Schema**

The seeder must output Parquet files identical to Layer 1's output schema (RawIssue model).

| Column | Generator Logic |
| :---- | :---- |
| id | Sequential Integer |
| project\_id | Input Argument (e.g., 101, 102\) |
| labels | List sampled from a pre-defined set (type::bug, severity::high, etc.) |
| work\_item\_type | Weighted choice: 80% ISSUE, 20% TASK |
| parent\_id | If Task: Random ID from previously generated Issues. |

## **3\. Performance Benchmarks (KPIs)**

The testing suite passes if the following benchmarks are met on standard hardware (e.g., 4-core CPU, 16GB RAM):

### **3.1. Layer 2 Processing Speed**

* **Input:** 50,000 Issues across 5 projects.  
* **Max Duration:** \< 2.0 seconds.  
* **Verification:** Run python \-m cProfile \-s time app/processor/main.py.

### **3.2. Layer 3 Dashboard Latency**

* **Cold Start (Load Data):** \< 1.0 second (reading 50k rows from Parquet).  
* **Interaction (Filter Change):** \< 200ms (Pandas in-memory filtering).  
* **Constraint:** The UI must not "freeze" when rendering the Aging Boxplot for 50k points.

## **4\. Test Scenarios**

### **Scenario A: The "Big Data" Stress Test**

1. Run Seeder: python tools/seeder.py \--count 500000 (Half a million issues).  
2. Run Layer 2 Processor.  
3. Open Layer 3 Dashboard.  
   * *Pass:* Dashboard loads without MemoryError.  
   * *Pass:* Time range slider responds smoothly.

### **Scenario B: The "Quality Rules" Logic Test**

1. Configure rules.yaml to require severity::\* for all Bugs.  
2. Run Seeder with \--inject-errors.  
3. Run Layer 2 Processor.  
4. Inspect data/analytics/data\_quality.parquet.  
   * *Pass:* The file contains rows with error code MISSING\_LABEL.  
   * *Pass:* The file does *not* contain valid features.

## **5\. Architecture Decision Records (ADR)**

### **5.1. Why Faker \+ Numpy?**

* **Faker:** Generates realistic text (titles, usernames) which makes the dashboard look "real" during demos or UAT (User Acceptance Testing).  
* **Numpy:** Used for vectorized date generation. Generating dates loop-by-loop in Python is too slow for massive datasets.

### **5.2. Why Bypass Layer 1?**

* **determinism:** Layer 1 depends on network latency and API state. By seeding data/processed directly, we isolate Layer 2/3 performance metrics from network fluctuations.

## **6. Integration Testing (Live GitLab Seeder)**

While the efficient "Bypass" strategy is used for performance testing, **Layer 1 (Collector)** must be tested against a real GitLab API to verify:
1.  **Rate Limit Handling:** Does the collector back off correctly?
2.  **Schema Compliance:** Does the API response match our expected `RawIssue` model?
3.  **Authentication:** Is the Token handling valid?

### **6.1. Tool: `tools/gitlab_seeder.py`**

A CLI tool to populate a **blank** GitLab repository with known test data.

**Requirements:**
1.  **Safety:** Must require a `--project-id` and explicit user confirmation (or `--force` flag) before writing.
2.  **Structure Setup:**
    *   Create standard labels (`type::bug`, `workflow::review`, etc.).
    *   Create standard milestones (`v1.0`, `v1.1`) with Start/Due dates.
3.  **Data Seeding:**
    *   Push N issues (e.g., 50) via `python-gitlab`.
    *   **Hierarchy:** Support `Task` creation and reliable parent-child linking via **GraphQL mutations** (bypassing unreliable Quick Actions).
    *   **Error Injection:** Support `--inject-errors` flag to introduce data quality issues:
        *   Missing Labels (e.g., no `type::*`).
        *   Conflicting Labels (e.g., `type::bug` AND `type::feature`).
        *   Missing Milestones.
    *   Assign pseudo-random labels and milestones.

### **6.2. Workflow**
1.  User creates a Sandbox Project on GitLab.com or Self-Managed.
2.  User runs: `uv run python tools/gitlab_seeder.py --project-id 12345 --count 50`.
3.  User runs Layer 1: `uv run python app/collector/orchestrator.py --project-id 12345 --full-sync`.
4.  Verification: `data/processed/issues_12345.parquet` exists and contains 50 rows.
