# **Technical Specification: Risk & Capacity View**

**Scope:** Specification for a new dashboard view focusing on "Team Health," "Workload Distribution," and "Delivery Risk." This view aims to identify bottlenecks and context-switching risks without acting as a performance surveillance tool.

## **1. Concept: Capacity & Health**

We shift focus from "Velocity" (past performance) to **"Current Commitment"** (active load).

### **1.1. Key Metrics**
*   **WIP Load:** Number of active issues assigned per person.
*   **Weight Distribution:** Sum of issue weights per person (if available) to account for task complexity.
*   **Context Switching Factor:** Number of distinct "Contexts" (e.g., Projects, Iterations) a developer is simultaneously active in.

---

## **2. Layer 2: Logic & Configuration**

### **2.1. Enrichment Logic**
*   **Assignee Normalization:**
    *   `None` / `null` assignees must be mapped to `"Unassigned"`.
    *   This is crucial for identifying "Risk of latent work" (work presumed started but owned by no one).
*   **Anonymization (Privacy):**
    *   Support a configuration flag `anonymize_users: bool` in `rules.yaml`.
    *   If `True`, hash or replace usernames (e.g., `User A`, `User B`) before passing to Layer 3.
    *   **Goal:** Allow analysis of *structural* problems (e.g., "One person has 90% of the work") without targeting individuals.

### **2.2. Configuration (`default.yaml`)**
Add section for capacity rules:
```yaml
capacity:
  max_wip_per_person: 5
  max_contexts_per_person: 2
  anonymize_users: false
  hidden_users: ["support-bot", "release-manager"]
```

---

## **3. Layer 3: Presentation (Dashboard)**

A new **"Capacity"** view (or tab) in the main dashboard.

### **3.1. Workload Balancer (Stacked Bar Chart)**
*   **Goal:** Visually identify overloaded team members and bottleneck stages.
*   **X-Axis:** Assignee.
*   **Y-Axis:** Count of Open Issues (or Sum of Weights).
*   **Stacks (Color):** `Workflow Stage` (Using the semantic colors from `rules.yaml`).
*   **Interaction:** Clicking a bar filters the generic Issue Detail Grid.
*   **Insight:**
    *   High "Review" stack: Bottleneck for others (Senior Dev trap).
    *   High "Implementation" stack: Delivery risk.

### **3.2. Context Switching Matrix (Heatmap)**
*   **Goal:** Identify efficiency loss due to multitasking.
*   **X-Axis:** Contexts (e.g., `R&D`, `Customer A`, `Legacy`).
*   **Y-Axis:** Assignee.
*   **Value:** Count of active issues.
*   **Insight:** Developers active in >2 columns are likely suffering from high context-switching costs.

### **3.3. Unassigned Work (Risk Indicator)**
*   **Component:** Metric Card or separate Bar Chart.
*   **Metric:** Count of `active` issues with `assignee="Unassigned"`.
*   **Why:** High unassigned WIP indicates work that started but was dropped or forgotton.

---

## **4. Data Privacy & Governance**

*   **Principles:**
    1.  **Aggregate First:** Default views should show team-level distribution.
    2.  **Opt-Out:** `rules.yaml` allows excluding specific functional accounts (e.g., bots).
    3.  **Positive Framing:** Metrics are framed as "Risk" (Process issue) rather than "Productivity" (Person issue).