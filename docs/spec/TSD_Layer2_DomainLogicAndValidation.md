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
