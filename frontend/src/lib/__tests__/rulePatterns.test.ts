import { describe, expect, it } from "vitest";
import {
  countMatchingLabels,
  describePattern,
  parsePattern,
  serializePattern,
} from "../rulePatterns";

describe("parsePattern", () => {
  it("treats a bare value as exact", () => {
    expect(parsePattern("type::bug")).toEqual({ mode: "exact", value: "type::bug" });
  });

  it("reads each prefix", () => {
    expect(parsePattern("contains:project::A")).toEqual({
      mode: "contains",
      value: "project::A",
    });
    expect(parsePattern("regex:^iteration-\\d+$")).toEqual({
      mode: "regex",
      value: "^iteration-\\d+$",
    });
    expect(parsePattern("exact:regex:x")).toEqual({ mode: "exact", value: "regex:x" });
  });
});

describe("serializePattern", () => {
  it("writes exact values bare", () => {
    expect(serializePattern({ mode: "exact", value: "type::bug" })).toBe("type::bug");
  });

  it("keeps the exact prefix when the value looks like a prefix", () => {
    expect(serializePattern({ mode: "exact", value: "regex:x" })).toBe("exact:regex:x");
    expect(serializePattern({ mode: "exact", value: "contains:y" })).toBe("exact:contains:y");
    expect(serializePattern({ mode: "exact", value: "exact:z" })).toBe("exact:exact:z");
  });

  it("round-trips every shape", () => {
    for (const raw of ["a", "contains:a", "regex:^a$", "exact:regex:a", "exact:exact:a"]) {
      expect(serializePattern(parsePattern(raw))).toBe(raw);
    }
  });
});

describe("describePattern", () => {
  it("describes each mode", () => {
    expect(describePattern("type::bug")).toBe("type::bug");
    expect(describePattern("contains:project::A")).toBe('contains "project::A"');
    expect(describePattern("regex:^iteration-\\d+$")).toBe("pattern ^iteration-\\d+$");
  });
});

describe("countMatchingLabels", () => {
  const labels = ["type::bug", "type::feature", "Type::bug"];

  it("counts exact and contains case-sensitively", () => {
    expect(countMatchingLabels("type::bug", labels)).toBe(1);
    expect(countMatchingLabels("contains:type::", labels)).toBe(2);
    expect(countMatchingLabels("contains:nothing", labels)).toBe(0);
  });

  it("returns null for regex", () => {
    expect(countMatchingLabels("regex:^type", labels)).toBeNull();
  });
});
