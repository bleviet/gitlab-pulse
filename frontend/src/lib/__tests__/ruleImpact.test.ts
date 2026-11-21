import { describe, expect, it } from "vitest";
import { changedGroups, formatDelta, groupsForSection, mergeProblems } from "../ruleImpact";
import type { ImpactSummary } from "../types";

const impact: ImpactSummary = {
  total_issues: 10,
  project_ids: [1],
  types: [
    { name: "Bug", before: 3, after: 5 },
    { name: null, before: 7, after: 5 },
  ],
  severities: [{ name: null, before: 1, after: 1 }],
  priorities: [{ name: null, before: 2, after: 2 }],
  stages: [{ name: "Doing", before: 4, after: 4 }],
  contexts: [{ name: null, before: 0, after: 1 }],
  quality: [
    { name: "STALE", before: 2, after: 1 },
    { name: "MISSING_LABEL", before: 0, after: 0 },
    { name: "SOMETHING_NEW", before: 1, after: 1 },
  ],
  unmapped_labels: [],
  unmapped_label_total: 0,
  label_pattern_counts: {},
  title_pattern_counts: {},
};

describe("groupsForSection", () => {
  it("maps each section to its group with deltas", () => {
    const [group] = groupsForSection("type", impact);
    expect(group.title).toBe("Issues by type");
    expect(group.rows.map((r) => [r.label, r.before, r.after, r.delta])).toEqual([
      ["Bug", 3, 5, 2],
      ["No type", 7, 5, -2],
    ]);
    expect(groupsForSection("stages", impact)[0].title).toBe("Issues by stage");
    expect(groupsForSection("stages", impact)[0].rows[0].label).toBe("Doing");
  });

  it("labels empty names per group", () => {
    expect(groupsForSection("severity", impact)[0].rows[0].label).toBe("No severity");
    expect(groupsForSection("priority", impact)[0].rows[0].label).toBe("No priority");
    expect(groupsForSection("contexts", impact)[0].rows[0].label).toBe("No context");
  });

  it("uses plain quality labels and keeps unknown codes", () => {
    const [group] = groupsForSection("quality", impact);
    expect(group.title).toBe("Issues flagged");
    expect(group.rows.map((r) => r.label)).toEqual([
      "Stale",
      "Missing a required label",
      "SOMETHING_NEW",
    ]);
  });

  it("gives rows unique keys", () => {
    const keys = groupsForSection("type", impact)[0].rows.map((r) => r.key);
    expect(new Set(keys).size).toBe(keys.length);
  });
});

describe("formatDelta", () => {
  it("formats signs with a true minus", () => {
    expect(formatDelta(19)).toBe("+19");
    expect(formatDelta(-4)).toBe("−4");
    expect(formatDelta(0)).toBe("");
  });
});

describe("mergeProblems", () => {
  it("keeps the first problem for each path", () => {
    const merged = mergeProblems(
      [{ path: "a", message: "x" }],
      [
        { path: "a", message: "x" },
        { path: "a", message: "y" },
      ],
    );
    expect(merged).toEqual([{ path: "a", message: "x" }]);
  });
});

describe("changedGroups and overview sections", () => {
  it("lists only groups with a change, changed rows first", () => {
    const groups = changedGroups(impact);
    expect(groups.map((g) => g.title)).toEqual(["Issues by type", "Issues by context", "Issues flagged"]);
    expect(groups[0].rows.map((r) => r.label)).toEqual(["Bug", "No type"]);
  });

  it("is empty when nothing changed", () => {
    const same: ImpactSummary = {
      ...impact,
      types: [{ name: "Bug", before: 1, after: 1 }],
      contexts: [],
      quality: [],
    };
    expect(changedGroups(same)).toEqual([]);
  });

  it("projects and history show every group", () => {
    expect(groupsForSection("history", impact).length).toBe(6);
  });
});
