import { describe, expect, it } from "vitest";
import { filterIssuesBySearch, normalizeSearchText } from "../search";
import type { IssueItem } from "../types";

function makeIssue(partial: Partial<IssueItem>): IssueItem {
  return {
    id: 1,
    iid: 11,
    project_id: 101,
    title: "Stabilize auth redirect",
    state: "opened",
    created_at: "2026-11-01T00:00:00+00:00",
    updated_at: "2026-11-02T00:00:00+00:00",
    closed_at: null,
    labels: [],
    contexts: ["customer"],
    work_item_type: "ISSUE",
    parent_id: null,
    child_ids: [],
    web_url: null,
    assignee: "alex",
    milestone: "v1.2",
    milestone_id: 1,
    milestone_due_date: null,
    milestone_start_date: null,
    age_days: 5,
    cycle_time: null,
    is_stale: false,
    issue_type: "Bug",
    severity: "High",
    priority: "high",
    priority_rank: 0,
    team: "default",
    stage: "Review",
    stage_type: "waiting",
    stage_order: 2,
    days_in_stage: 4,
    quality_signals: [],
    quality_hints: [],
    ...partial,
  };
}

describe("search", () => {
  it("normalizes label separators and whitespace", () => {
    expect(normalizeSearchText(["priority::1", "workflow::review"])).toBe(
      "priority 1 workflow review",
    );
  });

  it("matches exact multi-token queries across multiple columns", () => {
    const items = [
      makeIssue({ id: 1, assignee: "alex", contexts: ["customer"], milestone: "v1.2", priority: "high" }),
      makeIssue({ id: 2, assignee: "sam", contexts: ["platform"], milestone: "v1.3", priority: "medium" }),
    ];

    const matched = filterIssuesBySearch(items, "alex customer v1.2 high");
    expect(matched.map((i) => i.id)).toEqual([1]);
  });

  it("falls back to fuzzy matching only when exact token match finds nothing", () => {
    const items = [
      makeIssue({ id: 1, priority: "critical", title: "Improve milestone summary" }),
      makeIssue({ id: 2, priority: "low", title: "Routine cleanup" }),
    ];

    expect(filterIssuesBySearch(items, "critcal").map((i) => i.id)).toEqual([1]);
    expect(filterIssuesBySearch(items, "summary").map((i) => i.id)).toEqual([1]);
  });
});
