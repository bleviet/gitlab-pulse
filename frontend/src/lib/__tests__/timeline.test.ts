import { describe, expect, it } from "vitest";
import { buildMilestoneTimelineData, naturalCompare } from "../timeline";
import type { IssueItem } from "../types";

function makeMsIssue(partial: Partial<IssueItem>): IssueItem {
  return {
    id: 1,
    iid: 1,
    project_id: 101,
    title: "Issue",
    state: "opened",
    created_at: "2026-10-01T00:00:00+00:00",
    updated_at: "2026-10-02T00:00:00+00:00",
    closed_at: null,
    labels: [],
    contexts: [],
    work_item_type: "ISSUE",
    parent_id: null,
    child_ids: [],
    web_url: null,
    assignee: "alex",
    milestone: "v1.0",
    milestone_id: 10,
    milestone_due_date: "2026-11-30T00:00:00+00:00",
    milestone_start_date: null,
    age_days: 5,
    cycle_time: null,
    is_stale: false,
    issue_type: "Task",
    severity: null,
    priority: "P2",
    priority_rank: 1,
    team: "default",
    stage: "Implementation",
    stage_type: "active",
    stage_order: 1,
    days_in_stage: 2,
    quality_signals: [],
    quality_hints: [],
    ...partial,
  };
}

describe("timeline", () => {
  it("orders versions naturally", () => {
    const sorted = ["v2.4.10", "v2.4.2", "v2.4.9"].sort(naturalCompare);
    expect(sorted).toEqual(["v2.4.2", "v2.4.9", "v2.4.10"]);
  });

  it("classifies milestone statuses, hides closed undated milestones, and alternates laneY", () => {
    const now = new Date("2026-11-18T00:00:00Z");
    const issues: IssueItem[] = [
      makeMsIssue({ id: 1, milestone: "v1.1", state: "opened", milestone_due_date: "2026-10-10T00:00:00Z" }),
      makeMsIssue({ id: 2, milestone: "v1.2", state: "closed", milestone_due_date: "2026-10-20T00:00:00Z" }),
      makeMsIssue({ id: 3, milestone: "v1.3", state: "opened", milestone_due_date: "2026-12-10T00:00:00Z" }),
      makeMsIssue({ id: 4, milestone: "v2.4.10", state: "opened", milestone_due_date: null }),
      makeMsIssue({ id: 5, milestone: "v2.4.9", state: "opened", milestone_due_date: null }),
      makeMsIssue({ id: 6, milestone: "old-undated", state: "closed", milestone_due_date: null }),
    ];

    const model = buildMilestoneTimelineData(issues, {}, "v1.3", now);
    expect(model).not.toBeNull();
    const titles = model!.points.map((p) => p.title);
    expect(titles).toEqual(["v1.1", "v1.2", "v1.3", "v2.4.9", "v2.4.10"]);
    expect(model!.points.map((p) => p.status)).toEqual([
      "Overdue",
      "Complete",
      "On Track",
      "Unscheduled",
      "Unscheduled",
    ]);
    expect(model!.points.map((p) => p.laneY)).toEqual([1, -1, 1, -1, 1]);
    expect(model!.points[2].isHighlighted).toBe(true);
    expect(model!.points[0].isDimmed).toBe(true);
    expect(model!.separatorTimeMs).not.toBeNull();
  });
});
