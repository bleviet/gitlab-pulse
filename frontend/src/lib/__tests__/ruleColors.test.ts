import { describe, expect, it } from "vitest";
import {
  canReset,
  colorGroups,
  effectiveColor,
  isOverridden,
  normalizeHex,
  parseColorPath,
  removeColorEntry,
  resetColor,
  setColor,
} from "../ruleColors";
import type { PaletteDefaults, RuleSetBody } from "../types";

const defaults: PaletteDefaults = {
  light: { bug: "#111111", primary: "#222222", odd_key: "#333333" },
  dark: { bug: "#aaaaaa", primary: "#bbbbbb", odd_key: "#cccccc" },
};

describe("effectiveColor", () => {
  it("prefers theme map, then global, then flat, then defaults", () => {
    const colors = {
      light: { Bug: "#010101" },
      global: { bug: "#020202", primary: "#030303" },
      primary: "#040404",
      accent: "#050505",
    };
    expect(effectiveColor(colors, defaults, "light", "bug")).toBe("#010101");
    expect(effectiveColor(colors, defaults, "dark", "bug")).toBe("#020202");
    expect(effectiveColor(colors, defaults, "dark", "primary")).toBe("#040404");
    expect(effectiveColor({ primary: "#040404" }, defaults, "dark", " Primary ")).toBe("#040404");
    expect(effectiveColor({}, defaults, "dark", "bug")).toBe("#aaaaaa");
    expect(effectiveColor({}, defaults, "dark", "nothing")).toBeNull();
  });
});

describe("order of shared entries and group names", () => {
  it("lets the later of global and flat entries win", () => {
    const flatLast = { global: { bug: "#010101" }, bug: "#020202" };
    const globalLast = { bug: "#020202", global: { bug: "#010101" } };
    expect(effectiveColor(flatLast, defaults, "dark", "bug")).toBe("#020202");
    expect(effectiveColor(globalLast, defaults, "dark", "bug")).toBe("#010101");
  });

  it("finds group maps case-insensitively and writes into the existing one", () => {
    const colors = { Light: { Bug: "#010101" }, GLOBAL: { task: "#020202" } };
    expect(effectiveColor(colors, defaults, "light", "bug")).toBe("#010101");
    expect(effectiveColor(colors, defaults, "dark", "task")).toBe("#020202");
    expect(isOverridden(colors, "light", "bug")).toBe(true);
    const next = setColor(colors, "light", "bug", "#123456");
    expect(Object.keys(next)).toEqual(["Light", "GLOBAL"]);
    expect(next.Light).toEqual({ bug: "#123456" });
  });

  it("writes into the last group whose name matches", () => {
    const colors = { light: { bug: "#010101" }, Light: { task: "#020202" } };
    const next = setColor(colors, "light", "bug", "#123456");
    expect(next.light).toEqual({ bug: "#010101" });
    expect(next.Light).toEqual({ task: "#020202", bug: "#123456" });
    expect(effectiveColor(next, defaults, "light", "bug")).toBe("#123456");
  });

  it("parses and removes entries without splitting key dots", () => {
    expect(parseColorPath("colors.Light.my.key")).toEqual({ kind: "theme", group: "light", key: "my.key" });
    expect(parseColorPath("colors.global.a")).toEqual({ kind: "global", key: "a" });
    expect(parseColorPath("colors.a.b")).toEqual({ kind: "flat", key: "a.b" });
    const colors = { Light: { "my.key": "#1", other: "#2" }, "a.b": "#3" };
    expect(removeColorEntry(colors, "colors.Light.my.key")).toEqual({
      Light: { other: "#2" },
      "a.b": "#3",
    });
    expect(removeColorEntry(colors, "colors.a.b")).toEqual({ Light: colors.Light });
  });
});

describe("reset keeps the other theme and respects built-in colours", () => {
  it("copies a shared colour into the other theme before removing it", () => {
    const colors = { global: { bug: "#010101" } };
    const next = resetColor(colors, "light", "bug");
    expect(effectiveColor(next, defaults, "light", "bug")).toBe("#111111");
    expect(effectiveColor(next, defaults, "dark", "bug")).toBe("#010101");
    const flat = resetColor({ bug: "#020202" }, "dark", "bug");
    expect(effectiveColor(flat, defaults, "light", "bug")).toBe("#020202");
    expect(effectiveColor(flat, defaults, "dark", "bug")).toBe("#aaaaaa");
  });

  it("enables reset only when the colour differs from the built-in one", () => {
    expect(canReset({ light: { bug: "#111111" } }, defaults, "light", "bug")).toBe(false);
    expect(canReset({ light: { bug: "#111" } }, defaults, "light", "bug")).toBe(false);
    expect(canReset({ light: { bug: "#999999" } }, defaults, "light", "bug")).toBe(true);
    expect(canReset({}, defaults, "light", "bug")).toBe(false);
    expect(canReset({ light: { custom: "#999999" } }, defaults, "light", "custom")).toBe(true);
  });
});

describe("setColor, resetColor, isOverridden", () => {
  it("writes into the theme map and keeps other entries", () => {
    const colors = { dark: { task: "#000000" }, flat: "#ffffff" };
    const next = setColor(colors, "light", "Bug", "#123456");
    expect(next).toEqual({ dark: { task: "#000000" }, flat: "#ffffff", light: { bug: "#123456" } });
    expect(colors).toEqual({ dark: { task: "#000000" }, flat: "#ffffff" });
    expect(isOverridden(next, "light", "bug")).toBe(true);
    expect(isOverridden(next, "dark", "bug")).toBe(false);
  });

  it("removes theme, global and flat entries on reset", () => {
    const colors = { light: { bug: "#1" }, dark: { bug: "#2" }, global: { bug: "#3" }, bug: "#4" };
    const next = resetColor(colors, "light", "bug");
    expect(next).toEqual({ light: {}, dark: { bug: "#2" }, global: {} });
    expect(isOverridden(next, "light", "bug")).toBe(false);
    expect(isOverridden(next, "dark", "bug")).toBe(true);
  });

  it("removes an offending entry by problem path", () => {
    const colors = { global: { a: "x", b: "y" }, light: { c: "z" }, flat: "q" };
    expect(removeColorEntry(colors, "colors.global.a")).toEqual({
      global: { b: "y" },
      light: { c: "z" },
      flat: "q",
    });
    expect(removeColorEntry(colors, "colors.flat")).toEqual({
      global: { a: "x", b: "y" },
      light: { c: "z" },
    });
  });
});

describe("colorGroups", () => {
  const rule = {
    classification: [
      { name: "type", values: [{ name: "Bug" }, { name: "Incident" }] },
      { name: "priority", values: [{ name: "P4" }] },
    ],
  } as unknown as RuleSetBody;

  it("adds custom values without defaults and an Other group", () => {
    const groups = colorGroups(defaults, rule);
    const types = groups.find((g) => g.title === "Issue types");
    expect(types?.rows.map((r) => r.key)).toEqual(["bug", "feature", "task", "epic", "incident"]);
    expect(types?.rows.find((r) => r.key === "incident")).toEqual({
      key: "incident",
      label: "Incident",
      hasDefault: false,
    });
    expect(types?.rows[0].hasDefault).toBe(true);
    expect(groups.find((g) => g.title === "Priority")?.rows.map((r) => r.key)).toEqual([
      "p1",
      "p2",
      "p3",
      "p4",
    ]);
    const other = groups[groups.length - 1];
    expect(other.title).toBe("Other");
    expect(other.rows.map((r) => r.key)).toEqual(["odd_key"]);
  });
});

describe("custom colour rows", () => {
  it("skips keys of built-in rows and hints about shared colours", () => {
    const rule = {
      classification: [
        { name: "type", values: [{ name: "Low" }, { name: "Incident" }, { name: "Bug" }] },
      ],
    } as unknown as RuleSetBody;
    const groups = colorGroups(
      { light: { ...defaults.light, incident: "#555555" }, dark: defaults.dark },
      rule,
    );
    const types = groups.find((g) => g.title === "Issue types");
    expect(types?.rows.map((r) => r.key)).toEqual(["bug", "feature", "task", "epic", "incident"]);
    expect(types?.rows.find((r) => r.key === "incident")?.hasDefault).toBe(true);
    expect(types?.hints).toEqual(['"Low" uses the same colour as Severity "Low".']);
  });
});

describe("normalizeHex", () => {
  it("accepts 3 and 6 digit hex in any case", () => {
    expect(normalizeHex("#ABC")).toBe("#aabbcc");
    expect(normalizeHex(" #AaBbCc ")).toBe("#aabbcc");
    expect(normalizeHex("abc")).toBeNull();
    expect(normalizeHex("#abcd")).toBeNull();
    expect(normalizeHex("#ggg")).toBeNull();
  });
});
