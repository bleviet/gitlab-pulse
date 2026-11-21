import { describe, expect, it } from "vitest";
import { buildScopeSuggestions, scoreScopeCandidate } from "../scopeSearch";
import type { GlobalFilters, IssueItem } from "../types";

function makeIssue(partial: Partial<IssueItem>): IssueItem {
  return {
    id: 1,
    iid: 1,
    project_id: 101,
    title: "Issue",
    state: "opened",
    created_at: "2026-11-10T00:00:00+00:00",
    updated_at: "2026-11-11T00:00:00+00:00",
    closed_at: null,
    labels: [],
    contexts: [],
    work_item_type: "ISSUE",
    parent_id: null,
    child_ids: [],
    web_url: null,
    assignee: "alex",
    milestone: "v1.4",
    milestone_id: 1,
    milestone_due_date: null,
    milestone_start_date: null,
    age_days: 2,
    cycle_time: null,
    is_stale: false,
    issue_type: "Bug",
    impact: "High",
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

const DEFAULT_FILTERS: GlobalFilters = {
  team: "All",
  context: "All",
  milestone: "All",
  startDate: "2026-01-01",
  endDate: "2026-11-18",
  preset: "all",
};

describe("scopeSearch", () => {
  it("scores exact, prefix, word-prefix, compact, subsequence, and fuzzy typo candidates", () => {
    expect(scoreScopeCandidate("project::A", "project::A")).toBe(100);
    expect(scoreScopeCandidate("project::A", "proj")).toBe(90);
    expect(scoreScopeCandidate("project::A", "proj a")).toBe(84);
    expect(scoreScopeCandidate("v1.4", "v14")).toBe(100);
    expect(scoreScopeCandidate("project::A", "prja")).toBe(62);
    expect(scoreScopeCandidate("project::A", "proejct")).toBeGreaterThan(0);
    expect(scoreScopeCandidate("project::A", "login crash")).toBe(0);
  });

  it("lists contexts and milestones in browse mode and hides single-team group", () => {
    const issues = [
      makeIssue({ id: 1, team: "default", contexts: ["project::A"], milestone: "v1.4" }),
      makeIssue({ id: 2, team: "default", contexts: ["project::A", "project::B"], milestone: "v1.4" }),
      makeIssue({ id: 3, team: "default", contexts: ["project::B"], milestone: "v1.5" }),
    ];
    const options = {
      teams: ["default"],
      contexts: ["project::A", "project::B"],
      milestones: ["v1.4", "v1.5"],
    };

    const res = buildScopeSuggestions(issues, DEFAULT_FILTERS, options, "");
    expect(res.combined).toEqual([]);
    expect(res.teams).toEqual([]);
    expect(res.contexts.map((c) => [c.value, c.count])).toEqual([
      ["project::A", 2],
      ["project::B", 2],
    ]);
    expect(res.milestones.map((m) => [m.value, m.count])).toEqual([
      ["v1.4", 2],
      ["v1.5", 1],
    ]);

    const multiTeamRes = buildScopeSuggestions(
      [
        ...issues,
        makeIssue({ id: 4, team: "platform", contexts: ["project::C"], milestone: "v1.5" }),
      ],
      DEFAULT_FILTERS,
      { teams: ["default", "platform"], contexts: [...options.contexts, "project::C"], milestones: options.milestones },
      "",
    );
    expect(multiTeamRes.teams.map((t) => [t.value, t.count])).toEqual([
      ["default", 3],
      ["platform", 1],
    ]);
  });

  it("suggests combined multi-dimension matches for 'proj v14' and 'proj a v14'", () => {
    const issues = [
      makeIssue({ id: 1, contexts: ["project::A"], milestone: "v1.4" }),
      makeIssue({ id: 2, contexts: ["project::A"], milestone: "v1.4" }),
      makeIssue({ id: 3, contexts: ["project::B"], milestone: "v1.4" }),
      makeIssue({ id: 4, contexts: ["project::B"], milestone: "v1.5" }),
    ];
    const options = {
      teams: ["default"],
      contexts: ["project::A", "project::B"],
      milestones: ["v1.4", "v1.5"],
    };

    const broad = buildScopeSuggestions(issues, DEFAULT_FILTERS, options, "proj v14");
    expect(broad.combined.map((c) => [c.patch, c.count])).toEqual([
      [{ context: "project::A", milestone: "v1.4" }, 2],
      [{ context: "project::B", milestone: "v1.4" }, 1],
    ]);
    expect(broad.contexts.map((c) => c.value)).toEqual(["project::A", "project::B"]);
    expect(broad.milestones.map((m) => m.value)).toEqual(["v1.4"]);

    const narrow = buildScopeSuggestions(issues, DEFAULT_FILTERS, options, "proj a v14");
    expect(narrow.combined).toHaveLength(1);
    expect(narrow.combined[0].patch).toEqual({ context: "project::A", milestone: "v1.4" });
    expect(narrow.combined[0].count).toBe(2);

    const reversed = buildScopeSuggestions(issues, DEFAULT_FILTERS, options, "v14 proj a");
    expect(reversed.combined).toHaveLength(1);
    expect(reversed.combined[0].patch).toEqual({ context: "project::A", milestone: "v1.4" });
  });

  it("omits zero-count combinations and returns empty lists when unmatched", () => {
    const issues = [
      makeIssue({ id: 1, contexts: ["project::A"], milestone: "v1.5" }),
      makeIssue({ id: 2, contexts: ["project::B"], milestone: "v1.4" }),
    ];
    const options = {
      teams: ["default"],
      contexts: ["project::A", "project::B"],
      milestones: ["v1.4", "v1.5"],
    };

    const zeroCombo = buildScopeSuggestions(issues, DEFAULT_FILTERS, options, "proj a v14");
    expect(zeroCombo.combined).toEqual([]);

    const unmatched = buildScopeSuggestions(issues, DEFAULT_FILTERS, options, "login crash");
    expect(unmatched).toEqual({ combined: [], teams: [], contexts: [], milestones: [] });
  });
});
