import { describe, expect, it } from "vitest";
import {
  buildNewRuleSetBody,
  getCategory,
  isDirty,
  moveItem,
  problemsByPath,
  problemsWithPrefix,
  removeAt,
  setCategoryValues,
  teamNameInUse,
  updateAt,
  validateRuleSet,
} from "../ruleDraft";
import type { RuleSetBody } from "../types";

function makeRule(): RuleSetBody {
  return {
    project_ids: [1],
    team: "Core",
    classification: [
      {
        name: "type",
        values: [
          { name: "Bug", labels: ["type::bug"], title: [] },
          { name: "Feature", labels: ["type::feature"], title: [] },
        ],
      },
      { name: "custom", values: [{ name: "X", labels: ["x"], title: [] }] },
    ],
    contexts: { rules: [{ name: "Web", labels: ["ctx::web"], title: [] }], require_assignment: false },
    workflow: {
      stages: [
        { name: "Doing", labels: ["doing"], type: "active", description: "" },
        { name: "Review", labels: ["review"], type: "waiting", description: "" },
      ],
    },
    validation: {
      required_labels: { Bug: ["impact::high"] },
      required_fields: {},
      stale_threshold_days: 30,
      max_cycle_time_days: 60,
    },
    colors: { anything: 1 },
  };
}

describe("list helpers", () => {
  it("moveItem swaps neighbours and ignores out-of-range moves", () => {
    expect(moveItem([1, 2, 3], 0, 1)).toEqual([2, 1, 3]);
    expect(moveItem([1, 2, 3], 2, -1)).toEqual([1, 3, 2]);
    const list = [1, 2, 3];
    expect(moveItem(list, 0, -1)).toBe(list);
    expect(moveItem(list, 2, 1)).toBe(list);
  });

  it("updateAt and removeAt do not mutate", () => {
    const list = [{ a: 1 }, { a: 2 }];
    expect(updateAt(list, 1, { a: 9 })).toEqual([{ a: 1 }, { a: 9 }]);
    expect(removeAt(list, 0)).toEqual([{ a: 2 }]);
    expect(list).toEqual([{ a: 1 }, { a: 2 }]);
  });
});

describe("categories", () => {
  it("returns an empty list for a missing category", () => {
    expect(getCategory(makeRule(), "impact")).toEqual([]);
  });

  it("creates a missing category at the end and preserves others", () => {
    const rule = makeRule();
    const next = setCategoryValues(rule, "impact", [{ name: "High", labels: ["h"], title: [] }]);
    expect(next.classification.map((c) => c.name)).toEqual(["type", "custom", "impact"]);
    expect(next.classification[0]).toBe(rule.classification[0]);
    expect(next.classification[1]).toBe(rule.classification[1]);
  });

  it("replaces an existing category in place", () => {
    const next = setCategoryValues(makeRule(), "type", []);
    expect(next.classification.map((c) => c.name)).toEqual(["type", "custom"]);
    expect(getCategory(next, "type")).toEqual([]);
  });
});

describe("isDirty", () => {
  it("is false for equal copies and true for a pure reorder", () => {
    const base = makeRule();
    expect(isDirty(base, makeRule())).toBe(false);
    const reordered = setCategoryValues(base, "type", moveItem(getCategory(base, "type"), 0, 1));
    expect(isDirty(base, reordered)).toBe(true);
  });
});

describe("validateRuleSet", () => {
  it("accepts a valid rule set", () => {
    expect(validateRuleSet(makeRule())).toEqual([]);
  });

  it("flags empty and duplicate classification names", () => {
    const rule = makeRule();
    const values = [
      { name: " ", labels: [], title: [] },
      { name: "Bug", labels: [], title: [] },
      { name: "Bug", labels: [], title: [] },
    ];
    const paths = validateRuleSet(setCategoryValues(rule, "type", values)).map((p) => p.path);
    expect(paths).toEqual(["classification.type.0.name", "classification.type.2.name"]);
  });

  it("flags stage problems", () => {
    const rule = makeRule();
    rule.workflow.stages = [
      { name: "A", labels: ["contains:"], type: "active", description: "" },
      { name: "A", labels: [], type: "bogus", description: "" },
      { name: "", labels: [], type: "completed", description: "" },
    ];
    expect(validateRuleSet(rule).map((p) => p.path)).toEqual([
      "workflow.stages.0.labels.0",
      "workflow.stages.1.name",
      "workflow.stages.1.type",
      "workflow.stages.2.name",
    ]);
  });

  it("flags context problems and empty patterns in title and required labels", () => {
    const rule = makeRule();
    rule.contexts.rules = [
      { name: "Web", labels: [], title: ["regex:"] },
      { name: "Web", labels: [], title: [] },
    ];
    rule.validation.required_labels = { Bug: ["exact:"] };
    expect(validateRuleSet(rule).map((p) => p.path)).toEqual([
      "contexts.rules.0.title.0",
      "contexts.rules.1.name",
      "validation.required_labels.Bug.0",
    ]);
  });

  it("flags thresholds that are not integers of at least 1", () => {
    const rule = makeRule();
    rule.validation.stale_threshold_days = 0;
    rule.validation.max_cycle_time_days = 2.5;
    expect(validateRuleSet(rule).map((p) => p.path)).toEqual([
      "validation.stale_threshold_days",
      "validation.max_cycle_time_days",
    ]);
  });
});

describe("problem lookups", () => {
  const problems = [
    { path: "classification.type.0.labels.2", message: "a" },
    { path: "classification.type.0.labels.2", message: "dup" },
    { path: "classification.type.1.name", message: "b" },
  ];

  it("keys problems by path, keeping the first message", () => {
    expect(problemsByPath(problems)).toEqual({
      "classification.type.0.labels.2": "a",
      "classification.type.1.name": "b",
    });
  });

  it("collects the trailing index under a prefix", () => {
    expect(problemsWithPrefix(problemsByPath(problems), "classification.type.0.labels")).toEqual({
      2: "a",
    });
  });
});

describe("team and project checks", () => {
  it("flags an empty team name", () => {
    const rule = { ...makeRule(), team: " " };
    expect(validateRuleSet(rule).map((p) => p.path)).toEqual(["team"]);
  });

  it("flags an empty project list while another default exists", () => {
    const rule = { ...makeRule(), project_ids: [] };
    const context = { otherDefaultExists: true, claimedBy: {}, savedProjectIds: [1] };
    expect(validateRuleSet(rule, context).map((p) => p.path)).toEqual(["project_ids"]);
    expect(validateRuleSet(rule, { ...context, otherDefaultExists: false })).toEqual([]);
    expect(validateRuleSet(rule)).toEqual([]);
  });

  it("names every claimed project and team in one problem", () => {
    const rule = { ...makeRule(), project_ids: [101, 102, 103] };
    const problems = validateRuleSet(rule, {
      otherDefaultExists: false,
      claimedBy: { 101: "Backend", 102: "Platform" },
      savedProjectIds: [],
    });
    expect(problems).toEqual([
      {
        path: "project_ids",
        message: "Project 101 already belongs to Backend, and Project 102 to Platform.",
      },
    ]);
  });

  it("skips project checks when the project list is unchanged", () => {
    const rule = { ...makeRule(), project_ids: [1, 2] };
    const context = {
      otherDefaultExists: true,
      claimedBy: { 1: "Platform" },
      savedProjectIds: [2, 1],
    };
    expect(validateRuleSet(rule, context)).toEqual([]);
    expect(validateRuleSet({ ...rule, project_ids: [1] }, context)).toHaveLength(1);
  });
});

describe("teamNameInUse", () => {
  it("compares case-insensitively and ignores blanks", () => {
    expect(teamNameInUse(" core ", ["Core"])).toBe(true);
    expect(teamNameInUse("Other", ["Core"])).toBe(false);
    expect(teamNameInUse("", [""])).toBe(false);
  });
});

describe("buildNewRuleSetBody", () => {
  it("copies the rules with a new team and projects, keeping colors", () => {
    const base = makeRule();
    const next = buildNewRuleSetBody(base, " Mobile ", [4, 5]);
    expect(next.team).toBe("Mobile");
    expect(next.project_ids).toEqual([4, 5]);
    expect(next.colors).toBe(base.colors);
    expect(next.classification).toBe(base.classification);
    expect(base.team).toBe("Core");
  });
});
