# **Technical Specification: Layer 2 \- Domain Logic & Validation**

**Scope:** Implementation details for modular rules, metrics calculation, and data quality filtering.

## **1\. Configuration Engine**

### **1.1. Modular Rule Loader**

The service scans app/config/rules/\*.yaml. Each file must follow the DomainRule schema.

* **Conflict Detection:** If two YAML files claim the same GitLab project\_id, the service must abort with a ConfigurationConflictError.

## **2\. Enrichment & Validation Engine**

### **2.1. Vectorized Metrics (Pandas)**

Calculations are performed on the entire DataFrame to ensure high performance.

* **Aging:** df\['age\_days'\] \= (now \- df\['created\_at'\]).days.  
* **Cycle Time:** df\['cycle\_time'\] \= (df\['closed\_at'\] \- df\['created\_at'\]).days.

### **2.2. Validation Logic**

The "Gatekeeper" checks each issue against the rules defined in the corresponding YAML:

* **Required Labels:** Check if type::bug issues have a severity:: label.  
* **Staleness:** Tag issues as is\_stale if updated\_at \> max\_stale\_days.

### **2.3. Context Slicing (Data Explosion)**

To support "Platform Development" patterns where one repo serves multiple projects, the processor employs "Data Explosion":

*   **Config:** Rules define contexts via label prefixes (e.g., `rnd::Alpha`, `cust::Beta`).
*   **Expansion:** A single issue with labels `rnd::Alpha` and `cust::Beta` is expanded into two rows in the analytics dataset.
    *   Row 1: `{id: 100, context: "Alpha", context_group: "R&D"}`
    *   Row 2: `{id: 100, context: "Beta", context_group: "Customer"}`
*   **Validation:** If `require_context_assignment` is true, issues without any matching context label are flagged as `MISSING_CONTEXT` quality failures.

## **3\. Data Output (Split Storage)**

| File | Content |
| :---- | :---- |
| issues\_valid.parquet | Only issues that passed all YAML-defined rules. |
| data\_quality.parquet | Failed issues \+ error\_code (e.g., MISSING\_LABEL, STALE\_WITHOUT\_UPDATE). |

## **4\. Architecture Decision Records (ADR)**

### **4.1. Why Pandas Vectorization?**

* **Efficiency:** Calculating age for 100,000 issues using a Python for loop takes seconds; using Pandas vectorization takes milliseconds. In an analytics tool, sub-second processing is the standard.

### **4.2. Why Modular YAML Rules?**

* **Decentralization:** Different teams/projects have different definitions of "Quality." Modular rules allow project A to require milestones while project B focuses purely on labels, without them sharing a single monolithic config file.
