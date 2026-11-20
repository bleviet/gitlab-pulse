import { describe, expect, it } from "vitest";
import {
  describeUnplacedProblem,
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
    expect(placed.map((p) => p.message)).toEqual(["a"]);
    expect(unplaced.map((p) => p.message)).toEqual(["b", "c"]);
    expect(sectionForPath("project_ids")).toBeNull();
  });
});

describe("describeUnplacedProblem", () => {
  it("prefixes classification problems with category and value name", () => {
    expect(
      describeUnplacedProblem({ path: "classification.component.0.labels.0", message: "Bad." }, rule),
    ).toBe('component "Core": Bad.');
  });

  it("leaves other messages as they are", () => {
    expect(describeUnplacedProblem({ path: "project_ids", message: "Bad." }, rule)).toBe("Bad.");
  });
});
