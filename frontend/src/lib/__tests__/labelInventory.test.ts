import { describe, expect, it } from "vitest";
import { buildLabelInventory } from "../labelInventory";
import type { IssueItem } from "../types";

function issue(labels: string[]): IssueItem {
  return { labels } as IssueItem;
}

describe("buildLabelInventory", () => {
  const styles = {
    "type::bug": { color: "#d9534f", text_color: "#ffffff" },
    unused: { color: "#111111", text_color: "#eeeeee" },
  };

  it("counts issues per label and sorts by count then name", () => {
    const items = buildLabelInventory(
      [issue(["b", "type::bug"]), issue(["b", "a"]), issue(["b", "b"])],
      styles,
    );
    expect(items.map((i) => [i.name, i.count])).toEqual([
      ["b", 3],
      ["a", 1],
      ["type::bug", 1],
      ["unused", 0],
    ]);
  });

  it("includes styled labels with zero usage and uses their colors", () => {
    const items = buildLabelInventory([], styles);
    const unused = items.find((i) => i.name === "unused");
    expect(unused).toEqual({
      name: "unused",
      color: "#111111",
      textColor: "#eeeeee",
      count: 0,
    });
  });

  it("uses null colors for labels without a style", () => {
    const [item] = buildLabelInventory([issue(["plain"])], {});
    expect(item).toEqual({ name: "plain", color: null, textColor: null, count: 1 });
  });
});
