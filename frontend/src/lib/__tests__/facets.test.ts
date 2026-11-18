import { describe, expect, it } from "vitest";
import {
  applyFacets,
  applyGlobalFilters,
  buildFacetChips,
  buildUrlSearch,
  parseUrlState,
  withoutFacet,
} from "../facets";
import type { GlobalFilters, IssueItem } from "../types";

function makeIssue(overrides: Partial<IssueItem> = {}): IssueItem {
  return {
    id: 1,
    iid: 1,
    project_id: 101,
    title: "Sample issue",
    state: "opened",
    created_at: "2026-11-10T10:00:00+00:00",
    updated_at: "2026-11-11T10:00:00+00:00",
    closed_at: null,
    labels: ["type::bug"],
    contexts: [],
    work_item_type: "ISSUE",
    parent_id: null,
    child_ids: [],
    web_url: "https://gitlab.example/issues/1",
    assignee: "ann",
    milestone: "v1",
    milestone_id: 1,
    milestone_due_date: null,
    milestone_start_date: null,
    age_days: 5,
    cycle_time: null,
    is_stale: false,
    issue_type: "Bug",
    severity: "High",
    priority: "P1",
    priority_rank: 0,
    team: "default",
    stage: "Review",
    stage_type: "waiting",
    stage_order: 2,
    days_in_stage: 3,
    quality_signals: [],
    quality_hints: [],
    ...overrides,
  };
}

describe("facets", () => {
  const sample: IssueItem[] = [
    makeIssue({ id: 1, stage: "Review", state: "opened", priority: "P1", contexts: ["project::A", "project::B"] }),
    makeIssue({ id: 2, stage: "Review", state: "opened", priority: "P2", milestone: null, quality_signals: ["MISSING_MILESTONE"] }),
    makeIssue({ id: 3, stage: "Backlog", state: "opened", priority: "Unset", assignee: "Unassigned" }),
    makeIssue({ id: 4, stage: "Done", state: "closed", priority: "P1", closed_at: "2026-11-15T12:00:00+00:00" }),
  ];

  it("defaults to opened issues when state facet is omitted", () => {
    const res = applyFacets(sample, {});
    expect(res.map((i) => i.id)).toEqual([1, 2, 3]);
  });

  it("filters by stage, priority, issue_type, state, signal, and recent", () => {
    const now = new Date("2026-11-18T12:00:00Z");
    expect(applyFacets(sample, { stage: "Review", priority: "P1" }, now).map((i) => i.id)).toEqual([1]);
    expect(applyFacets(sample, { state: "closed", priority: "P1" }, now).map((i) => i.id)).toEqual([4]);
    expect(applyFacets(sample, { signal: "MISSING_MILESTONE" }, now).map((i) => i.id)).toEqual([2]);
    expect(applyFacets(sample, { state: "closed", recent: "closed" }, now).map((i) => i.id)).toEqual([4]);
    expect(applyFacets(sample, { priority: "Unset" }, now).map((i) => i.id)).toEqual([3]);

    const typedSample = [
      ...sample,
      makeIssue({ id: 5, stage: "Review", state: "opened", issue_type: null }),
      makeIssue({ id: 6, stage: "Review", state: "opened", issue_type: "Feature" }),
    ];
    expect(applyFacets(typedSample, { issue_type: "Feature" }, now).map((i) => i.id)).toEqual([6]);
    expect(applyFacets(typedSample, { issue_type: "Unset" }, now).map((i) => i.id)).toEqual([5]);
  });

  it("round-trips valid URL parameters and drops malformed ones", () => {
    const compactSearch = buildUrlSearch(false, "open", {
      stage: "Review",
      state: "closed",
      issue_type: "Bug",
      recent: "closed",
      query: "login",
    });
    expect(compactSearch).toContain("view=compact");
    expect(compactSearch).toContain("f_issue_type=Bug");
    expect(parseUrlState(compactSearch)).toEqual({
      chartsVisible: false,
      summaryId: "open",
      facets: {
        stage: "Review",
        state: "closed",
        issue_type: "Bug",
        recent: "closed",
        query: "login",
      },
    });

    const defaultSearch = buildUrlSearch(true, null, { stage: "Review" });
    expect(defaultSearch).not.toContain("view=");
    expect(parseUrlState(defaultSearch)).toEqual({
      chartsVisible: true,
      summaryId: null,
      facets: { stage: "Review" },
    });

    expect(parseUrlState("?view=analytics&f_stage=Review")).toEqual({
      chartsVisible: true,
      summaryId: null,
      facets: { stage: "Review" },
    });

    const dirty = parseUrlState("?view=other&f_state=deleted&f_day=bad&f_day_kind=created");
    expect(dirty).toEqual({ chartsVisible: true, summaryId: null, facets: {} });
  });

  it("removes day_kind when removing day facet and emits sidebar chips", () => {
    expect(withoutFacet({ day: "2026-11-15", day_kind: "closed", state: "closed" }, "day")).toEqual({
      state: "closed",
    });

    const gf: GlobalFilters = {
      team: "default",
      context: "project::A",
      milestone: "v1",
      startDate: "2026-11-01",
      endDate: "2026-11-18",
      preset: "30d",
    };
    const chips = buildFacetChips({ stage: "Review", issue_type: "Bug" }, gf, "2026-01-01", "2026-11-18");
    expect(chips.map((c) => c.label)).toEqual([
      "Stage: Review",
      "Type: Bug",
      "Domain / Team: default",
      "Context: project::A",
      "Milestone: v1",
      "Time: 30 Days",
    ]);

    expect(applyGlobalFilters(sample, gf).map((i) => i.id)).toEqual([1]);
  });
});
