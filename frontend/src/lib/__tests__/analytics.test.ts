import { describe, expect, it } from "vitest";
import {
  buildDailyVelocityData,
  buildIssueTypeDonutData,
  buildStagePriorityBars,
  formatShare,
} from "../analytics";
import { getOverviewStages, getWorkflowStages } from "../board";
import { contrastTextForHex } from "../colors";
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

describe("analytics helpers", () => {
  it("selects accessible foreground contrast text for hex fills", () => {
    expect(contrastTextForHex("#f4a44a")).toBe("#0b0d17");
    expect(contrastTextForHex("#56d4b0")).toBe("#0b0d17");
    expect(contrastTextForHex("#dd2476")).toBe("#ffffff");
    expect(contrastTextForHex("#b51c3c")).toBe("#ffffff");
    expect(contrastTextForHex("#3d5370")).toBe("#ffffff");
    expect(contrastTextForHex("#fff")).toBe("#0b0d17");
    expect(contrastTextForHex("#000")).toBe("#ffffff");
    expect(contrastTextForHex("var(--accent)")).toBe("#ffffff");
  });

  it("includes closed stages in getWorkflowStages while preserving open-only getOverviewStages", () => {
    const issues = [
      makeIssue({ id: 1, stage: "Done", stage_order: 6, state: "closed" }),
      makeIssue({ id: 2, stage: "Review", stage_order: 3, state: "opened" }),
      makeIssue({ id: 3, stage: "Architecture", stage_order: 1, state: "opened" }),
    ];

    expect(getOverviewStages(issues)).toEqual(["Architecture", "Review"]);
    expect(getWorkflowStages(issues)).toEqual(["Architecture", "Review", "Done"]);
  });

  it("builds stage bars for opened, closed-only, and mixed stages with accurate filterState", () => {
    const issues = [
      makeIssue({ id: 1, stage: "Architecture", stage_order: 1, state: "opened", priority: "P1", priority_rank: 0 }),
      makeIssue({ id: 2, stage: "Architecture", stage_order: 1, state: "opened", priority: "P2", priority_rank: 1 }),
      makeIssue({ id: 3, stage: "Done", stage_order: 6, state: "closed", priority: "P1", priority_rank: 0 }),
      makeIssue({ id: 4, stage: "Done", stage_order: 6, state: "closed", priority: "P1", priority_rank: 0 }),
      makeIssue({ id: 5, stage: "Review", stage_order: 3, state: "opened", priority: "P1", priority_rank: 0 }),
      makeIssue({ id: 6, stage: "Review", stage_order: 3, state: "closed", priority: "P2", priority_rank: 1 }),
    ];

    const stages = getWorkflowStages(issues);
    const buckets = buildStagePriorityBars(issues, stages, {}, ["P1", "P2"], "dark");

    expect(buckets.map((b) => b.stage)).toEqual(["Architecture", "Review", "Done"]);

    expect(buckets[0]).toMatchObject({
      stage: "Architecture",
      total: 2,
      filterState: "opened",
      isClosedOnly: false,
    });
    expect(buckets[0].bars.map((bar) => [bar.priority, bar.count])).toEqual([
      ["P1", 1],
      ["P2", 1],
    ]);

    expect(buckets[1]).toMatchObject({
      stage: "Review",
      total: 2,
      filterState: "all",
      isClosedOnly: false,
    });
    expect(buckets[1].bars.map((bar) => [bar.priority, bar.count])).toEqual([
      ["P1", 1],
      ["P2", 1],
    ]);

    expect(buckets[2]).toMatchObject({
      stage: "Done",
      total: 2,
      filterState: "closed",
      isClosedOnly: true,
    });
    expect(buckets[2].bars.map((bar) => [bar.priority, bar.count])).toEqual([["P1", 2]]);
  });

  it("builds issue type donut data with canonical order, palette colors, and Unset last", () => {
    const issues = [
      makeIssue({ id: 1, state: "opened", issue_type: null }),
      makeIssue({ id: 2, state: "opened", issue_type: "Task" }),
      makeIssue({ id: 3, state: "opened", issue_type: "Bug" }),
      makeIssue({ id: 4, state: "opened", issue_type: "Bug" }),
      makeIssue({ id: 5, state: "opened", issue_type: "Feature" }),
      makeIssue({ id: 6, state: "opened", issue_type: "Incident" }),
      makeIssue({ id: 7, state: "closed", issue_type: "Epic" }),
    ];

    const model = buildIssueTypeDonutData(
      issues,
      "opened",
      { bug: "#f5576c", feature: "#56d4b0", task: "#4facfe", unset: "#7a8fa8" },
      "dark",
    );

    expect(model.total).toBe(6);
    expect(model.slices).toEqual([
      { label: "Bug", count: 2, color: "#f5576c" },
      { label: "Feature", count: 1, color: "#56d4b0" },
      { label: "Task", count: 1, color: "#4facfe" },
      { label: "Incident", count: 1, color: "#56d4b0" },
      { label: "Unset", count: 1, color: "#7a8fa8" },
    ]);
  });

  it("anchors daily velocity to now when recent activity exists, and to latest historical day otherwise", () => {
    const now = new Date("2026-11-19T12:00:00Z");
    const recentIssues = [
      makeIssue({ id: 1, created_at: "2026-11-17T08:00:00+00:00", state: "closed", closed_at: "2026-11-18T10:00:00+00:00" }),
    ];
    const recentDays = buildDailyVelocityData(recentIssues, now);
    expect(recentDays[0].isoDate).toBe("2026-11-13");
    expect(recentDays[6].isoDate).toBe("2026-11-19");
    expect(recentDays.find((d) => d.isoDate === "2026-11-17")?.created).toBe(1);
    expect(recentDays.find((d) => d.isoDate === "2026-11-18")?.closed).toBe(1);

    const historicalIssues = [
      makeIssue({ id: 2, created_at: "2026-08-05T08:00:00+00:00", closed_at: "2026-08-10T10:00:00+00:00", state: "closed" }),
    ];
    const historicalDays = buildDailyVelocityData(historicalIssues, now);
    expect(historicalDays[0].isoDate).toBe("2026-08-04");
    expect(historicalDays[6].isoDate).toBe("2026-08-10");
    expect(historicalDays.find((d) => d.isoDate === "2026-08-05")?.created).toBe(1);
    expect(historicalDays.find((d) => d.isoDate === "2026-08-10")?.closed).toBe(1);
  });
});

describe("formatShare", () => {
  it("returns 0% for an empty total", () => {
    expect(formatShare(3, 0)).toBe("0%");
  });

  it("shows <1% for tiny nonzero shares", () => {
    expect(formatShare(1, 1000)).toBe("<1%");
    expect(formatShare(0, 10)).toBe("0%");
  });

  it("rounds to whole percents", () => {
    expect(formatShare(1, 3)).toBe("33%");
    expect(formatShare(2, 3)).toBe("67%");
    expect(formatShare(1, 200)).toBe("1%");
  });

  it("returns 100% for the full total", () => {
    expect(formatShare(7, 7)).toBe("100%");
  });
});
