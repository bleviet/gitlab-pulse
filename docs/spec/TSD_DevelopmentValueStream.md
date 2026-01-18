# **Technical Specification: Development Value Stream**

**Scope:** Specification for tracking the "Idea to Production" workflow, focusing on Inventory (WIP) and Flow Health.

## **1. Concept: Value Stream Metrics**

Moving monitoring from "Counting Bugs" to "Measuring Flow." Since the architecture captures the **current state snapshot**, we focus on metrics derived from the current status of the board.

### **1.1. Key Metrics**
*   **WIP (Work in Progress):** Count of issues in each stage. Identifies bottlenecks (e.g., high "Review" count vs low "Test" count).
*   **Stage Staleness:** Median days in current stage. Identifies where items get stuck (e.g., "Architecture" items rotting for 45 days).
*   **Flow Efficiency Proxy:** Ratio of Active Stages (Implementation) vs. Waiting Stages (Ready for Review).

## **2. Layer 2: Logic & Configuration**

### **2.1. Rule Configuration (`rules.yaml`)**

We extend the `DomainRule` to map labels to logical process stages.

```yaml
workflow:
  # Ordered list of stages. Priority is top-down.
  stages:
    - name: "Architecture"
      labels: ["workflow::architecture", "status::design"]
      type: "active"  # or "waiting"
    - name: "Implementation"
      labels: ["workflow::implementation", "status::coding"]
      type: "active"
    - name: "Review"
      labels: ["workflow::review", "status::mr_open"]
      type: "waiting"
    - name: "Testing"
      labels: ["workflow::test", "status::validation"]
      type: "active"
    - name: "Done"
      labels: ["workflow::done", "status::released"]
      type: "completed"
```

### **2.2. Enrichment Logic (`enricher.py`)**

The `enrich_workflow_stage` function determines the current stage of an issue.

1.  **Default:** `stage="Backlog"`, `stage_type="waiting"`.
2.  **Priority Matching:** Iterate through configured stages in order.
3.  **Label Match:** If issue has *any* of the stage's labels:
    *   Assign `stage = stage_name`
    *   Assign `stage_type = stage_type`
    *   Stop (First match wins).

## **3. Layer 3: Presentation (Dashboard)**

A new **"Flow"** view provides insights into process health.

### **3.1. The Funnel (WIP by Stage)**
*   **Type:** Bar Chart (Horizontal or Vertical).
*   **Data:** Count of issues per `stage`.
*   **Sorting:** By defined workflow order (not count).

### **3.2. Stage Aging (Staleness)**
*   **Type:** Boxplot.
*   **X-Axis:** Stage.
*   **Y-Axis:** `days_in_stage` (calculated as `now - updated_at` as a proxy, or `update - label_added` if history available).
*   **Goal:** Highlight stages with high median age or extreme outliers.

## **4. Architecture Decision Records (ADR)**

### **4.1. Snapshot-based Workflow**
*   **Decision:** Calculate flow metrics from the *current* snapshot state (labels) rather than reconstructing full history.
*   **Why:** simpler to implement and provides immediate value for "Current Health". Future iterations can parse system notes for full cycle time analysis if needed.