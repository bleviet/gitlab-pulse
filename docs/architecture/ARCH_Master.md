# **Master Architecture: GitLabInsight**

Version: 1.0
Status: Finalized Specification  
Scope: Universal End-to-End Data Pipeline (Ingestion to Visualization)

## **1\. Executive Summary**

**GitLabInsight** is a versatile analytics platform designed to extract, validate, and visualize GitLab issue data for any user—from individual developers and open-source maintainers to large-scale organizations. It follows a **Clean Architecture** and a **Medallion Data Pattern** to ensure that raw technical data is transformed into meaningful metrics (like Aging and Throughput) without being restricted to any specific workflow or environment.

## **2\. Data Strategy & Storage Decisions**

The system uses a tiered storage approach, moving from high-volume raw files to high-performance analytical files, ensuring scalability for projects of any size.

### **2.1. The Data Layers**

| Layer | Name | Path | Description |
| :---- | :---- | :---- | :---- |
| **Layer 0** | **Raw** | data/raw/ | **Transient/Audit:** Unmodified JSON responses from GitLab. |
| **Layer 1** | **Processed** | data/processed/ | **Standardized Mirror:** Validated technical data (Parquet). |
| **Layer 2** | **Analytics** | data/analytics/ | **Gold:** Enriched, context-mapped metrics (Parquet). |
| **Layer 2** | **Quality** | data/analytics/ | **Exceptions:** Issues failing custom validation rules. |

### **2.2. ADR: Why persistent Raw storage?**

* **Reliability:** In any data-driven environment, it is critical to have a "Source of Truth." The Raw layer preserves the original API response as evidence of the state at the time of sync.  
* **Idempotency:** If the processing logic in Layer 1 changes (e.g., adding a new field), you can re-run the pipeline using the Raw files instead of re-querying GitLab. This prevents unnecessary network load and respects API rate limits.

## **3\. Layer 1: Data Acquisition (The Hybrid Collector)**

**Role:** Robust extraction and initial standardization.

### **3.1. Implementation Strategy**

* **REST API (python-gitlab):** Used for high-volume metadata retrieval (titles, labels, timestamps).  
* **GraphQL API:** Used specifically for **Hierarchy Resolution**. It resolves Parent-Child links (Issues to Tasks) not natively accessible via the REST Issue API, supporting modern GitLab work items.  
* **Incremental Sync:** Uses a sync\_state.json to track updated\_after timestamps, reducing API load by \>90%.

### **3.2. ADR: Why Pydantic for Ingestion?**

* **Data Integrity:** GitLab API responses can vary across versions and instances. Pydantic acts as a "strict gatekeeper," ensuring that every record in the processed layer adheres to a known schema.  
* **Validation vs. Dataclasses:** Pydantic provides built-in coercion (e.g., strings to datetime) and complex validation required for robust ingestion, which dataclasses lack out-of-the-box.

## **4\. Layer 2: Domain Logic & Validation**

**Role:** Applying context and calculating metrics.

### **4.1. Rules-Based Configuration (rules.yaml)**

To ensure flexibility across different use cases, the platform uses **Modular Rules**. Users can manage their own .yaml files in app/config/rules/ to define how data should be interpreted.

* **Mappings:** Maps technical labels (type::bug) to user-defined terms (Bug).  
* **Validation Rules:** Defines what constitutes "quality" for your specific project (e.g., "Every Feature must have a Milestone").

### **4.2. Performance Logic**

* **Pandas Vectorization:** All date-based metrics (age\_days, lead\_time) are calculated using vectorized Pandas operations rather than Python loops, allowing for near-instant processing of thousands of issues.  
* **The Gatekeeper:** Layer 2 splits data. Valid data goes to the Analytics file; invalid data goes to the Quality file, ensuring your insights are never skewed by poorly tagged issues.

### **4.3. Context Slicing (Data Explosion)**

Many organizations use a single GitLab repository for "Platform Development"—one codebase that serves multiple products, customers, or R&D initiatives. Since GitLab Free lacks sub-projects, teams use labels (e.g., `rnd::Alpha`, `cust::BMW`) to logically segment work.

**The Problem:** An issue (e.g., "Sensor Bug") may belong to *multiple* contexts (`rnd::Alpha` AND `rnd::Beta`). Project managers for each context need to see this issue in their respective dashboards.

**The Solution: Data Explosion**  
Layer 2 "explodes" the dataset. One physical issue becomes multiple logical rows in the analytics layer:

| Original Issue | Analytics Rows |
| :------------- | :------------- |
| Issue #100 (labels: `rnd::Alpha`, `rnd::Beta`) | Row 1: `context=Alpha`, Row 2: `context=Beta` |

**Why This Matters:**
* **Clean Architecture:** Layer 3 (Dashboard) remains "dumb"—it simply filters by the `context` column without needing to parse labels.
* **Quality Enforcement:** A validation rule (`require_context_assignment`) flags issues that aren't assigned to any context, enforcing team discipline.

## **5\. Layer 3: Presentation (Streamlit Dashboard)**

**Role:** High-speed visualization and drill-down.

### **5.1. UX Design System**

* **Semantic Palette:** Uses a unified color system (e.g., Bug=Red, Feature=Blue, Stale=Amber) across all charts to reduce cognitive load.  
* **Mode Adaptability:** The interface is designed to support both Dark and Light modes automatically, ensuring accessibility and contrast ratios (WCAG AA) are maintained in any environment.

### **5.2. UX Persona Strategy**

* **Strategic View:** High-level trends (Inflow vs. Outflow) and project velocity.  
* **Operational View:** Aging Boxplots (identifying bottlenecks) and the Stale Issue list to keep projects moving.  
* **Health & Hygiene View:** A dedicated screen showing the "Clean-up list" from the Quality layer, helping maintainers improve their project metadata.

### **5.3. ADR: Why Streamlit?**

* **Rapid Iteration:** Allows users to customize their own views directly in Python without needing web development expertise.  
* **Native Pandas Support:** Since our data is already in Parquet/Pandas format, the integration is seamless, making it highly efficient for local or server-side hosting.

## **6\. Testing & Validation Strategy**

**Role:** Ensuring performance and logic correctness without API dependency.

### **6.1. The "Bypass" Pattern**

To validate Layer 2 (Logic) and Layer 3 (UI Performance) without hitting GitLab API rate limits, the system includes a **Data Seeder**.

* **Tool:** tools/seeder.py  
* **Mechanism:** Generates synthetic Parquet files directly into data/processed/.  
* **Scale:** Capable of generating 100,000+ realistic records with injected "dirty data" (missing labels, conflicts) to verify validation rules and dashboard latency under load.

## **7\. System Structure Summary**

```bash
/  
├── app/  
│   ├── collector/          \# Layer 1: REST/GQL Hybrid Logic  
│   ├── processor/          \# Layer 2: Pandas/Pydantic Logic  
│   ├── dashboard/          \# Layer 3: Streamlit UI  
│   └── config/rules/       \# Modular .yaml rule files  
├── data/  
│   ├── raw/                \# L0 Output: JSON response dumps  
│   ├── processed/          \# L1 Output: Technical Mirror (Parquet)  
│   ├── analytics/          \# L2 Output: Trusted KPIs (Parquet)  
│   └── state/              \# Sync timestamps  
└── tools/  
    └── seeder.py           \# Synthetic data generator for testing
```

## **8\. Conclusion**

GitLabInsight is designed to scale with you. Whether you are a solo developer tracking a side project or a large organization managing hundreds of repositories, this architecture ensures that your data remains stable, your logic stays flexible, and your insights are always high-performing.
