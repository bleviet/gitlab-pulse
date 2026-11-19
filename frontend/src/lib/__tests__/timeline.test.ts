import { describe, expect, it } from "vitest";
import {
  buildMilestoneTimelineData,
  buildMonthTicks,
  buildUnscheduledMilestonesData,
  selectVisibleUnscheduledRows,
  naturalCompare,
} from "../timeline";
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

  it("classifies dated milestone statuses, skips undated ones, and alternates laneY", () => {
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
    expect(model!.points.map((p) => p.title)).toEqual(["v1.1", "v1.2", "v1.3"]);
    expect(model!.points.map((p) => p.status)).toEqual(["Overdue", "Complete", "On Track"]);
    expect(model!.points.map((p) => p.laneY)).toEqual([1, -1, 1]);
    expect(model!.points[2].isHighlighted).toBe(true);
    expect(model!.points[0].isDimmed).toBe(true);
    expect(model!.points[0].dueDateLabel).toBe("2026-10-10");
    expect("separatorTimeMs" in model!).toBe(false);
  });

  it("returns null when no milestone has a due date", () => {
    const issues = [makeMsIssue({ milestone: "v3", milestone_due_date: null })];
    expect(buildMilestoneTimelineData(issues, {}, null)).toBeNull();
  });

  it("builds month ticks on UTC month starts within range and under maxCount", () => {
    const minMs = Date.UTC(2026, 0, 15);
    const maxMs = Date.UTC(2026, 11, 20);
    const ticks = buildMonthTicks(minMs, maxMs, 4);
    expect(ticks.length).toBeGreaterThan(0);
    expect(ticks.length).toBeLessThanOrEqual(4);
    for (const tick of ticks) {
      const dt = new Date(tick.ms);
      expect(dt.getUTCDate()).toBe(1);
      expect(dt.getUTCHours()).toBe(0);
      expect(tick.ms).toBeGreaterThanOrEqual(minMs);
      expect(tick.ms).toBeLessThanOrEqual(maxMs);
    }
    expect(ticks[0].label).toBe("Feb 26");
    expect(buildMonthTicks(minMs, maxMs, 12)).toHaveLength(11);
  });

  it("summarizes unscheduled milestones from open issues", () => {
    const issues: IssueItem[] = [
      makeMsIssue({ id: 1, milestone: "v2.10", milestone_due_date: null, priority: "P1", priority_rank: 0, issue_type: "Bug", age_days: 10 }),
      makeMsIssue({ id: 2, milestone: "v2.10", milestone_due_date: null, priority: "P2", priority_rank: 1, issue_type: "Bug", age_days: 40 }),
      makeMsIssue({ id: 3, milestone: "v2.10", milestone_due_date: null, priority: "", priority_rank: null, issue_type: "", age_days: 3 }),
      makeMsIssue({ id: 4, milestone: "v2.10", milestone_due_date: null, state: "closed", age_days: 900 }),
      makeMsIssue({ id: 5, milestone: "v2.9", milestone_due_date: null, priority: "P2", priority_rank: 1, issue_type: "Task", age_days: 7 }),
      makeMsIssue({ id: 6, milestone: "Backlog", milestone_due_date: null, priority: "P2", priority_rank: 1, issue_type: "Task", age_days: 1 }),
      makeMsIssue({ id: 7, milestone: "Backlog", milestone_due_date: "2026-12-01T00:00:00Z" }),
      makeMsIssue({ id: 8, milestone: "Spike", milestone_due_date: null, state: "closed" }),
      makeMsIssue({ id: 9, milestone: "Spike2", milestone_due_date: null, state: "closed" }),
      makeMsIssue({ id: 10, milestone: null, milestone_due_date: null }),
    ];

    const model = buildUnscheduledMilestonesData(issues, {}, ["P1", "P2"], "dark");
    expect(model.rows.map((r) => r.title)).toEqual(["v2.10", "v2.9"]);
    expect(model.hiddenClosedCount).toBe(2);
    expect(model.openIssueCount).toBe(4);

    const top = model.rows[0];
    expect(top.openCount).toBe(3);
    expect(top.totalCount).toBe(4);
    expect(top.oldestOpenDays).toBe(40);
    expect(top.byPriority.map((s) => [s.label, s.count])).toEqual([
      ["P1", 1],
      ["P2", 1],
      ["Unset", 1],
    ]);
    expect(top.byType.map((s) => [s.label, s.count])).toEqual(
      expect.arrayContaining([
        ["Bug", 2],
        ["Unset", 1],
      ]),
    );
    expect(top.byType[top.byType.length - 1].label).toBe("Unset");
    expect(model.priorityLegend.map((s) => [s.label, s.count])).toEqual([
      ["P1", 1],
      ["P2", 2],
      ["Unset", 1],
    ]);
    expect(model.typeLegend.reduce((sum, s) => sum + s.count, 0)).toBe(4);
  });

  it("sorts unscheduled rows by open count, then natural title", () => {
    const issues: IssueItem[] = [
      makeMsIssue({ id: 1, milestone: "v2.10", milestone_due_date: null }),
      makeMsIssue({ id: 2, milestone: "v2.9", milestone_due_date: null }),
      makeMsIssue({ id: 3, milestone: "big", milestone_due_date: null }),
      makeMsIssue({ id: 4, milestone: "big", milestone_due_date: null }),
    ];
    const model = buildUnscheduledMilestonesData(issues, {}, [], "light");
    expect(model.rows.map((r) => r.title)).toEqual(["big", "v2.9", "v2.10"]);
  });

  it("pins the selected unscheduled row into the visible rows", () => {
    const issues: IssueItem[] = ["a", "b", "c", "d"].map((title, idx) =>
      makeMsIssue({ id: idx + 1, milestone: title, milestone_due_date: null }),
    );
    const { rows } = buildUnscheduledMilestonesData(issues, {}, [], "dark");
    const titles = (active: string | null) =>
      selectVisibleUnscheduledRows(rows, active, 2).map((r) => r.title);
    expect(titles(null)).toEqual(["a", "b"]);
    expect(titles("a")).toEqual(["a", "b"]);
    expect(titles("d")).toEqual(["a", "d"]);
    expect(titles("missing")).toEqual(["a", "b"]);
  });
});
