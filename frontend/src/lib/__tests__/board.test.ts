import { describe, expect, it } from "vitest";
import {
  computeLanePriorityCounts,
  getBoardLanes,
  getOverviewStages,
  sortIssuesHierarchy,
} from "../board";
import { buildSummaryGroups } from "../summary";
import type { IssueItem } from "../types";

function makeIssue(partial: Partial<IssueItem>): IssueItem {
  return {
    id: 1,
    iid: 1,
    project_id: 101,
    title: "Issue",
    state: "opened",
    created_at: "2026-11-16T00:00:00+00:00",
    updated_at: "2026-11-17T00:00:00+00:00",
    closed_at: null,
    labels: [],
    contexts: [],
    work_item_type: "ISSUE",
    parent_id: null,
    child_ids: [],
    web_url: null,
    assignee: "alex",
    milestone: "v1",
    milestone_id: 1,
    milestone_due_date: null,
    milestone_start_date: null,
    age_days: 2,
    cycle_time: null,
    is_stale: false,
    issue_type: "Bug",
    severity: "High",
    priority: "P1",
    priority_rank: 0,
    team: "default",
    stage: "Architecture",
    stage_type: "active",
    stage_order: 1,
    days_in_stage: 3,
    quality_signals: [],
    quality_hints: [],
    ...partial,
  };
}

describe("board and summary", () => {
  it("computes overview stages and aligned board lanes", () => {
    const issues = [
      makeIssue({ id: 1, stage: "Review", stage_order: 3, state: "opened" }),
      makeIssue({ id: 2, stage: "Architecture", stage_order: 1, state: "opened" }),
      makeIssue({ id: 3, stage: "Done", stage_order: 5, state: "closed" }),
    ];

    const stages = getOverviewStages(issues);
    expect(stages).toEqual(["Architecture", "Review"]);
    expect(getBoardLanes(stages, issues)).toEqual(["Architecture", "Review", "Done"]);
    expect(getBoardLanes(stages, [issues[2]])).toEqual(["Done"]);
  });

  it("sorts parent issues before children with depth", () => {
    const issues = [
      makeIssue({ id: 13, iid: 3, parent_id: 12, title: "grandchild" }),
      makeIssue({ id: 11, iid: 1, parent_id: null, title: "root" }),
      makeIssue({ id: 15, iid: 5, parent_id: 99, title: "orphan" }),
      makeIssue({ id: 12, iid: 2, parent_id: 11, title: "child" }),
    ];

    const rows = sortIssuesHierarchy(issues);
    expect(rows.map((r) => [r.issue.iid, r.depth])).toEqual([
      [1, 0],
      [2, 1],
      [3, 2],
      [5, 0],
    ]);
  });

  it("builds summary groups and lane priority counts in rank order with Unset last", () => {
    const now = new Date("2026-11-18T12:00:00Z");
    const issues = [
      makeIssue({ id: 1, stage: "Review", priority: "Unset", priority_rank: null }),
      makeIssue({ id: 2, stage: "Review", priority: "P2", priority_rank: 1 }),
      makeIssue({ id: 3, stage: "Review", priority: "P1", priority_rank: 0, quality_signals: ["MISSING_MILESTONE"] }),
      makeIssue({ id: 4, stage: "Done", state: "closed", priority: "P1", priority_rank: 0, closed_at: "2026-11-17T10:00:00Z" }),
    ];

    const laneCounts = computeLanePriorityCounts(issues, {}, ["P1", "P2"], "dark");
    expect(laneCounts.Review.map((e) => e.priority)).toEqual(["P1", "P2", "Unset"]);

    const summary = buildSummaryGroups(issues, {}, ["P1", "P2"], "dark", now);
    expect(summary[0].items.map((i) => [i.label, i.value])).toEqual([
      ["Open", 3],
      ["New 7d", 4],
      ["Closed 7d", 1],
    ]);
    expect(summary[1].items.map((i) => [i.label, i.value])).toEqual([
      ["P1", 1],
      ["P2", 1],
      ["Unset", 1],
    ]);
    expect(summary[2].items.find((i) => i.itemId === "hint_missing_milestone")?.value).toBe(1);
  });
});
