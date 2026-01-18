# **Glossary**

Definitions of key architectural patterns and terms used in GitLabInsight.

## **Medallion Architecture**

**Reference:** [Databricks Glossary: Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture)

The **Medallion Architecture** is a data design pattern used to logically organize data in a lakehouse, with the goal of incrementally and progressively improving the structure and quality of data as it flows through each layer of the architecture (from Bronze ⇒ Silver ⇒ Gold).

### **Implementation in GitLabInsight**

We adapt this pattern to our tiered data storage strategy:

| Medallion Layer | GitLabInsight Layer | Directory | Purpose |
| :--- | :--- | :--- | :--- |
| **Bronze (Raw)** | **Layer 0** | `data/raw/` | **Transient/Audit:** The "dump" of raw JSON responses from the GitLab API. Maintains the original state of the data source. |
| **Silver (Cleansed)** | **Layer 1** | `data/processed/` | **Standardized Mirror:** Data is validated, types are coerced (Pydantic), and stored in an optimized columnar format (Parquet). The schema is fixed, but business logic is not yet applied. |
| **Gold (Curated)** | **Layer 2** | `data/analytics/` | **Analytics Ready:** Business rules, label mappings, and computed metrics (e.g., Cycle Time, Staleness) are applied. This data is ready for consumption by validity-sensitive dashboards (Layer 3). |

---
