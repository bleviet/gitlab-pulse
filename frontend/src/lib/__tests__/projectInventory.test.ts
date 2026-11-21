import { describe, expect, it } from "vitest";
import { buildProjectInventory, knownProjects, projectLabel } from "../projectInventory";
import type { IssueItem, RuleSetItem } from "../types";

function issue(project_id: number, web_url: string | null): IssueItem {
  return { project_id, web_url } as IssueItem;
}

describe("buildProjectInventory", () => {
  it("derives names from issue URLs and counts issues", () => {
    const items = buildProjectInventory([
      issue(2, "https://gitlab.example.com/group/sub/project/-/issues/4"),
      issue(2, "https://gitlab.example.com/group/sub/project/-/issues/5"),
      issue(1, "https://gitlab.example.com/alpha/app/issues/1"),
    ]);
    expect(items).toEqual([
      { id: 1, name: "alpha/app", count: 1 },
      { id: 2, name: "group/sub/project", count: 2 },
    ]);
  });

  it("falls back to the project number and uses the first usable URL", () => {
    const items = buildProjectInventory([
      issue(7, null),
      issue(7, "not a url"),
      issue(8, null),
      issue(8, "https://h.example/g/p/-/issues/1"),
    ]);
    expect(items).toEqual([
      { id: 8, name: "g/p", count: 2 },
      { id: 7, name: "Project 7", count: 2 },
    ]);
  });
});

describe("projectLabel and knownProjects", () => {
  const inventory = [{ id: 1, name: "a/b", count: 3 }];

  it("labels unknown projects by number", () => {
    expect(projectLabel(1, inventory)).toBe("a/b");
    expect(projectLabel(9, inventory)).toBe("Project 9");
  });

  it("adds projects listed by rule sets or extra ids with zero issues", () => {
    const ruleSets = [{ rule: { project_ids: [5] } }] as unknown as RuleSetItem[];
    const known = knownProjects(inventory, ruleSets, [9, 1]);
    expect(known.map((p) => [p.id, p.count])).toEqual([
      [1, 3],
      [5, 0],
      [9, 0],
    ]);
  });
});
