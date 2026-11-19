import { describe, expect, it } from "vitest";
import {
  createEmptyStandupState,
  filterIssuesByCoverage,
  getLocalDateKey,
  markIssueOpened,
  nextCoveredFilterMode,
  parseStandupState,
  toggleIssueCovered,
} from "../standup";
import type { IssueItem } from "../types";

function makeIssue(id: number, iid = id): IssueItem {
  return {
    id,
    iid,
    project_id: 1,
    title: `Issue ${iid}`,
    state: "opened",
    created_at: "2026-03-01T10:00:00Z",
    updated_at: "2026-03-02T10:00:00Z",
    closed_at: null,
    labels: [],
    contexts: [],
    work_item_type: "Issue",
    parent_id: null,
    child_ids: [],
    web_url: `https://gitlab.example.com/group/proj/-/issues/${iid}`,
    assignee: "Alice",
    milestone: "v1.0",
    milestone_id: 10,
    milestone_due_date: null,
    milestone_start_date: null,
    age_days: 5,
    cycle_time: null,
    is_stale: false,
    issue_type: "Bug",
    severity: null,
    priority: "High",
    priority_rank: 1,
    team: "Core",
    stage: "In Progress",
    stage_type: "active",
    stage_order: 2,
    days_in_stage: 2,
    quality_signals: [],
    quality_hints: [],
  };
}

describe("standup daily coverage tracker", () => {
  it("formats local date as YYYY-MM-DD", () => {
    const d = new Date(2026, 10, 9, 8, 30, 0); // Nov 9, 2026 local
    expect(getLocalDateKey(d)).toBe("2026-11-09");
  });

  it("resets stored state when the stored date differs from today", () => {
    const yesterdayRaw = JSON.stringify({
      date: "2026-11-18",
      coveredIds: [101, 102],
      activeId: 102,
    });
    const parsed = parseStandupState(yesterdayRaw, "2026-11-19");
    expect(parsed).toEqual({
      date: "2026-11-19",
      coveredIds: [],
      activeId: null,
    });
  });

  it("restores valid state for today and deduplicates IDs", () => {
    const todayRaw = JSON.stringify({
      date: "2026-11-19",
      coveredIds: [101, 102, 101],
      activeId: 102,
    });
    const parsed = parseStandupState(todayRaw, "2026-11-19");
    expect(parsed).toEqual({
      date: "2026-11-19",
      coveredIds: [101, 102],
      activeId: 102,
    });
  });

  it("marks an opened issue as covered and currently active", () => {
    let state = createEmptyStandupState("2026-11-19");
    state = markIssueOpened(state, 101, "2026-11-19");
    expect(state).toEqual({
      date: "2026-11-19",
      coveredIds: [101],
      activeId: 101,
    });

    state = markIssueOpened(state, 205, "2026-11-19");
    expect(state).toEqual({
      date: "2026-11-19",
      coveredIds: [101, 205],
      activeId: 205,
    });

    // Clicking an already-covered issue updates activeId without duplicating
    state = markIssueOpened(state, 101, "2026-11-19");
    expect(state).toEqual({
      date: "2026-11-19",
      coveredIds: [101, 205],
      activeId: 101,
    });
  });

  it("toggles an issue covered state and clears activeId if unchecked", () => {
    let state = createEmptyStandupState("2026-11-19");
    state = markIssueOpened(state, 101, "2026-11-19");
    state = toggleIssueCovered(state, 202, "2026-11-19");
    expect(state).toEqual({
      date: "2026-11-19",
      coveredIds: [101, 202],
      activeId: 101,
    });

    // Unchecking the active issue clears activeId
    state = toggleIssueCovered(state, 101, "2026-11-19");
    expect(state).toEqual({
      date: "2026-11-19",
      coveredIds: [202],
      activeId: null,
    });
  });

  it("filters issues by coverage mode and cycles filter mode", () => {
    const issues = [makeIssue(1), makeIssue(2), makeIssue(3)];
    const covered = new Set<number>([2]);

    expect(filterIssuesByCoverage(issues, covered, "all").map((i) => i.id)).toEqual([1, 2, 3]);
    expect(filterIssuesByCoverage(issues, covered, "remaining").map((i) => i.id)).toEqual([1, 3]);
    expect(filterIssuesByCoverage(issues, covered, "covered").map((i) => i.id)).toEqual([2]);

    expect(nextCoveredFilterMode("all")).toBe("remaining");
    expect(nextCoveredFilterMode("remaining")).toBe("covered");
    expect(nextCoveredFilterMode("covered")).toBe("all");
  });
});
