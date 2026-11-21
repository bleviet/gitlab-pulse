import { describe, expect, it } from "vitest";
import { applySuggestions, suggestRows } from "../ruleSuggestions";
import type { LabelInventoryItem } from "../labelInventory";
import type { RuleSetBody } from "../types";

function inv(...entries: Array<[string, number]>): LabelInventoryItem[] {
  return entries.map(([name, count]) => ({ name, count, color: null, textColor: null }));
}

function rule(overrides: Partial<RuleSetBody> = {}): RuleSetBody {
  return {
    project_ids: [],
    team: "T",
    classification: [],
    contexts: { rules: [], require_assignment: false },
    workflow: { stages: [] },
    validation: {
      required_labels: {},
      required_fields: {},
      stale_threshold_days: 30,
      max_cycle_time_days: 60,
    },
    colors: {},
    ...overrides,
  };
}

describe("suggestRows", () => {
  it("uses the section scopes and names rows from the value", () => {
    const items = inv(["type::bug", 10], ["kind::in-progress_x", 2], ["priority::1", 4], ["other", 9]);
    expect(suggestRows("type", rule(), items).map((s) => s.name)).toEqual(["Bug", "In Progress X"]);
    const pri = suggestRows("priority", rule(), items);
    expect(pri.map((s) => s.name)).toEqual(["P1"]);
    expect(pri[0]).toMatchObject({ label: "priority::1", count: 4, existingRowIndex: null });
  });

  it("skips labels already covered, including contains patterns", () => {
    const r = rule({
      classification: [
        {
          name: "type",
          values: [
            { name: "Bug", labels: ["type::bug"], title: [] },
            { name: "Feat", labels: ["contains:type::fea"], title: [] },
          ],
        },
      ],
    });
    const items = inv(["type::bug", 1], ["type::feature", 1], ["type::task", 1]);
    expect(suggestRows("type", r, items).map((s) => s.label)).toEqual(["type::task"]);
  });

  it("points at an existing row with the same name", () => {
    const r = rule({
      classification: [{ name: "type", values: [{ name: "bug", labels: ["x"], title: [] }] }],
    });
    const [s] = suggestRows("type", r, inv(["type::bug", 1]));
    expect(s.existingRowIndex).toBe(0);
  });

  it("orders impact, priority and stages by rank", () => {
    const imp = suggestRows(
      "impact",
      rule(),
      inv(["impact::low", 1], ["impact::zzz", 1], ["severity::critical", 1], ["sev::major", 1]),
    );
    expect(imp.map((s) => s.name)).toEqual(["Critical", "Major", "Low", "Zzz"]);

    const pri = suggestRows(
      "priority",
      rule(),
      inv(["priority::high", 1], ["priority::2", 1], ["priority::10", 1], ["priority::1", 1]),
    );
    expect(pri.map((s) => s.name)).toEqual(["P1", "P2", "P10", "High"]);

    const stages = suggestRows(
      "stages",
      rule(),
      inv(["workflow::done", 1], ["workflow::review", 1], ["status::in-progress", 1], ["stage::todo", 1]),
    );
    expect(stages.map((s) => s.name)).toEqual(["Todo", "In Progress", "Review", "Done"]);
  });

  it("proposes stage kinds", () => {
    const stages = suggestRows(
      "stages",
      rule(),
      inv(["workflow::done", 1], ["workflow::qa", 1], ["workflow::coding", 1]),
    );
    const kinds = Object.fromEntries(stages.map((s) => [s.name, s.kind]));
    expect(kinds).toEqual({ Done: "completed", Qa: "waiting", Coding: "active" });
  });

  it("skips unused labels, empty names and Backlog stages", () => {
    expect(suggestRows("type", rule(), inv(["type::ghost", 0], ["type::-_", 3], ["type::ok", 1])).map((s) => s.name)).toEqual(["Ok"]);
    expect(suggestRows("stages", rule(), inv(["workflow::backlog", 5], ["status::Backlog", 2]))).toEqual([]);
  });

  it("returns nothing when no label matches", () => {
    expect(suggestRows("type", rule(), inv(["bug", 1], ["priority::1", 1]))).toEqual([]);
  });
});

describe("applySuggestions", () => {
  it("appends labels to existing rows and new rows at the end", () => {
    const r = rule({
      classification: [{ name: "type", values: [{ name: "Bug", labels: ["a"], title: [] }] }],
    });
    const chosen = suggestRows("type", r, inv(["type::bug", 1], ["type::task", 2], ["kind::task", 1]));
    const next = applySuggestions("type", r, chosen);
    const values = next.classification[0].values;
    expect(values.map((v) => [v.name, v.labels])).toEqual([
      ["Bug", ["a", "type::bug"]],
      ["Task", ["type::task", "kind::task"]],
    ]);
  });

  it("creates stages with the proposed kind", () => {
    const chosen = suggestRows("stages", rule(), inv(["workflow::done", 1]));
    const next = applySuggestions("stages", rule(), chosen);
    expect(next.workflow.stages).toEqual([
      { name: "Done", labels: ["workflow::done"], type: "completed", description: "" },
    ]);
  });
});
