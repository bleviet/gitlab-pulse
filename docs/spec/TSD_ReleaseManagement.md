# TSD: Release Management (Milestones)

## 1. Goal
Implement "Release Management" to track the scope (Milestone) dimension of the project.
This enables Project Managers to answer: "Is the release on track?" by visualizing scope completion, burn-up, and scope creep.

## 2. Concept: Milestones as First-Class Citizens
GitLab Milestones represent time-boxed releases (e.g., "v1.0", "Sprint 23").
By elevating Milestones in the data model, we can correlate:
- **Scope:** Total issues assigned to the milestone.
- **Progress:** Completed vs. Remaining work.
- **Predictability:** Burn-up charts showing if the deadline will be met.

## 3. Architecture Changes

### Layer 2: Domain Logic
1.  **Enrichment:**
    *   Ensure `milestone_id`, `milestone_title`, `milestone_due_date` are propagated.
    *   Calculate `release_status` (On Track, At Risk, Late) based on due date and progress.
2.  **Validation:**
    *   Add rule: `Features MUST have a milestone` (configurable).
    *   Flag "Orphaned Features" (no milestone).

### Layer 3: Presentation
New "Release" Dashboard View:
*   **Selector:** Filter by specific Milestone (default: active/next).
*   **Burn-up Chart:** Scope vs. Completed over time for the selected milestone.
*   **Readiness Gauge:** % Completed vs % Time Elapsed.
*   **Scope Creep:** Track added issues after start date.

## 4. Implementation Details

### Schema Updates (`app/processor/rule_loader.py`)
Add `MilestoneConfig` to `DomainRule`? 
Actually, we can extend `ValidationConfig` to include `required_fields`.

```python
class ValidationConfig(BaseModel):
    # ... existing ...
    required_fields: dict[str, list[str]] = Field(default_factory=dict) 
    # e.g., {"Feature": ["milestone_id"], "Bug": ["milestone_id"]}
```

### Dashboard (`app/dashboard/views/release.py`)
*   **Sidebar:** Add Milestone selector (Radio/Select).
*   **Charts:**
    *   **Burn-up:** 
        *   X-Axis: Time (Start to Due Date + Buffer).
        *   Lines: Total Scope (Count), Completed Scope (Count).
        *   Reference Line: Ideal Burn-up.
    
### Verification
*   Seeder must generate milestones and assign issues to them.
*   Verify "Missing Milestone" validation error works.
