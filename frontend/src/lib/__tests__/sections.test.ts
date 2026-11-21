import { describe, expect, it } from "vitest";
import {
  addLabelToRow,
  describeUnplacedProblem,
  rowNamesForSection,
  sectionForPath,
  splitProblems,
} from "../../components/settings/sections";
import type { RuleSetBody } from "../types";

const rule = {
  classification: [
    { name: "component", values: [{ name: "Core", labels: [], title: [] }] },
  ],
} as unknown as RuleSetBody;

describe("splitProblems", () => {
  it("separates problems that have no editor section", () => {
    const problems = [
      { path: "classification.type.0.name", message: "a" },
      { path: "project_ids", message: "b" },
      { path: "classification.component.0.labels.0", message: "c" },
    ];
    const { placed, unplaced } = splitProblems(problems);
    expect(placed.map((p) => p.message)).toEqual(["a", "b"]);
    expect(unplaced.map((p) => p.message)).toEqual(["c"]);
    expect(sectionForPath("project_ids")).toBe("projects");
    expect(sectionForPath("team")).toBe("projects");
  });
});

describe("describeUnplacedProblem", () => {
  it("prefixes classification problems with category and value name", () => {
    expect(
      describeUnplacedProblem({ path: "classification.component.0.labels.0", message: "Bad." }, rule),
    ).toBe('component "Core": Bad.');
  });

  it("leaves other messages as they are", () => {
    expect(describeUnplacedProblem({ path: "something", message: "Bad." }, rule)).toBe("Bad.");
  });
});

describe("addLabelToRow", () => {
  const full = {
    classification: [{ name: "type", values: [{ name: "Bug", labels: ["a"], title: [] }] }],
    workflow: { stages: [{ name: "Doing", labels: [], type: "active", description: "" }] },
    contexts: { rules: [{ name: "Web", labels: [], title: [] }], require_assignment: false },
  } as unknown as RuleSetBody;

  it("appends the bare label once to the chosen row", () => {
    const next = addLabelToRow(full, "type", 0, "regex:odd");
    expect(next.classification[0].values[0].labels).toEqual(["a", "exact:regex:odd"]);
    expect(addLabelToRow(next, "type", 0, "regex:odd")).toEqual(next);
    expect(addLabelToRow(full, "stages", 0, "x").workflow.stages[0].labels).toEqual(["x"]);
    expect(addLabelToRow(full, "contexts", 0, "y").contexts.rules[0].labels).toEqual(["y"]);
  });

  it("lists row names per section", () => {
    expect(rowNamesForSection(full, "stages")).toEqual(["Doing"]);
    expect(rowNamesForSection(full, "quality")).toEqual([]);
  });
});
