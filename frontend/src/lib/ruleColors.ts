import { getCategory } from "./ruleDraft";
import type { PaletteDefaults, RuleSetBody } from "./types";

export type ColorTheme = "light" | "dark";
export type ColorMap = Record<string, unknown>;

export interface ColorRow {
  key: string;
  label: string;
  hasDefault: boolean;
}

export interface ColorGroup {
  title: string;
  rows: ColorRow[];
  hints: string[];
}

const GROUPS = ["light", "dark", "global"];

const norm = (key: string): string => key.trim().toLowerCase();

function isMap(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function lookup(map: unknown, key: string): string | undefined {
  if (!isMap(map)) return undefined;
  let found: string | undefined;
  for (const [k, v] of Object.entries(map)) {
    if (norm(k) === key && typeof v === "string") found = v;
  }
  return found;
}

function without(map: Record<string, unknown>, key: string): Record<string, unknown> {
  return Object.fromEntries(Object.entries(map).filter(([k]) => norm(k) !== key));
}

function groupValue(colors: ColorMap, group: string, key: string): string | undefined {
  let found: string | undefined;
  for (const [name, value] of Object.entries(colors)) {
    if (norm(name) === group) found = lookup(value, key) ?? found;
  }
  return found;
}

function sharedValue(colors: ColorMap, key: string): string | undefined {
  let found: string | undefined;
  for (const [name, value] of Object.entries(colors)) {
    const n = norm(name);
    if (n === "global") found = lookup(value, key) ?? found;
    else if (!GROUPS.includes(n) && n === key && typeof value === "string") found = value;
  }
  return found;
}

export function normalizeHex(input: string): string | null {
  const match = /^#([0-9a-f]{3}|[0-9a-f]{6})$/i.exec(input.trim());
  if (!match) return null;
  const digits = match[1].toLowerCase();
  const full = digits.length === 3 ? [...digits].map((d) => d + d).join("") : digits;
  return `#${full}`;
}

export function effectiveColor(
  colors: ColorMap,
  defaults: PaletteDefaults,
  theme: ColorTheme,
  key: string,
): string | null {
  const k = norm(key);
  return (
    groupValue(colors, theme, k) ?? sharedValue(colors, k) ?? lookup(defaults[theme], k) ?? null
  );
}

export function isOverridden(colors: ColorMap, theme: ColorTheme, key: string): boolean {
  const k = norm(key);
  return groupValue(colors, theme, k) !== undefined || sharedValue(colors, k) !== undefined;
}

export function canReset(
  colors: ColorMap,
  defaults: PaletteDefaults,
  theme: ColorTheme,
  key: string,
): boolean {
  if (!isOverridden(colors, theme, key)) return false;
  const builtin = lookup(defaults[theme], norm(key));
  if (builtin === undefined) return true;
  const current = effectiveColor(colors, defaults, theme, key);
  return normalizeHex(current ?? "") !== normalizeHex(builtin);
}

export function setColor(
  colors: ColorMap,
  theme: ColorTheme,
  key: string,
  hex: string,
): ColorMap {
  const k = norm(key);
  const groupName =
    Object.keys(colors)
      .filter((n) => norm(n) === theme && isMap(colors[n]))
      .pop() ?? theme;
  const current = isMap(colors[groupName]) ? colors[groupName] : {};
  return { ...colors, [groupName]: { ...without(current, k), [k]: hex } };
}

function withoutShared(colors: ColorMap, theme: ColorTheme, key: string): ColorMap {
  const next: ColorMap = {};
  for (const [name, value] of Object.entries(colors)) {
    const n = norm(name);
    if ((n === theme || n === "global") && isMap(value)) next[name] = without(value, key);
    else if (n !== key || GROUPS.includes(n)) next[name] = value;
  }
  return next;
}

export function resetColor(colors: ColorMap, theme: ColorTheme, key: string): ColorMap {
  const k = norm(key);
  const other: ColorTheme = theme === "light" ? "dark" : "light";
  const shared = sharedValue(colors, k);
  let base = colors;
  if (shared !== undefined && groupValue(colors, other, k) === undefined) {
    base = setColor(colors, other, k, shared);
  }
  return withoutShared(base, theme, k);
}

export type ColorPathTarget =
  | { kind: "theme"; group: ColorTheme; key: string }
  | { kind: "global"; key: string }
  | { kind: "flat"; key: string }
  | { kind: "root" };

export function parseColorPath(path: string): ColorPathTarget {
  const rest = path.startsWith("colors.") ? path.slice(7) : path.startsWith("colors") ? "" : path;
  if (rest.trim() === "") return { kind: "root" };
  const lower = rest.toLowerCase();
  for (const group of GROUPS) {
    if (lower.startsWith(`${group}.`)) {
      const key = norm(rest.slice(group.length + 1));
      return group === "global" ? { kind: "global", key } : { kind: "theme", group: group as ColorTheme, key };
    }
  }
  return { kind: "flat", key: norm(rest) };
}

export function removeColorEntry(colors: ColorMap, path: string): ColorMap {
  const target = parseColorPath(path);
  if (target.kind === "root") return {};
  if (target.kind === "flat") {
    return Object.fromEntries(Object.entries(colors).filter(([name]) => norm(name) !== target.key));
  }
  const group = target.kind === "global" ? "global" : target.group;
  const next: ColorMap = {};
  for (const [name, value] of Object.entries(colors)) {
    next[name] = norm(name) === group && isMap(value) ? without(value, target.key) : value;
  }
  return next;
}

const BUILTIN: Array<[string, Array<[string, string]>]> = [
  [
    "Stage kinds",
    [
      ["active", "Active stages"],
      ["waiting", "Waiting stages"],
      ["completed", "Completed stages"],
      ["stale", "Stale issues"],
    ],
  ],
  [
    "Open and closed",
    [
      ["opened", "Opened"],
      ["closed", "Closed"],
    ],
  ],
  [
    "Milestones",
    [
      ["ms_on_track", "On track"],
      ["ms_overdue", "Overdue"],
      ["ms_complete", "Complete"],
      ["ms_incomplete", "Incomplete"],
      ["ms_highlight", "Highlighted"],
      ["ms_unscheduled", "No due date"],
      ["now_marker", "Today marker"],
    ],
  ],
  [
    "General",
    [
      ["primary", "Brand accent"],
      ["accent", "Secondary accent"],
      ["neutral", "Neutral"],
    ],
  ],
];

const CATEGORY_GROUPS: Array<[string, string, string[]]> = [
  ["Issue types", "type", ["bug", "feature", "task", "epic"]],
  ["Impact", "impact", ["critical", "high", "medium", "low", "unset"]],
  ["Priority", "priority", ["p1", "p2", "p3"]],
];

function titleCase(key: string): string {
  return key.charAt(0).toUpperCase() + key.slice(1);
}

export function colorGroups(defaults: PaletteDefaults, rule: RuleSetBody): ColorGroup[] {
  const hasDefault = (key: string): boolean => key in defaults.light || key in defaults.dark;
  const owners = new Map<string, { group: string; label: string }>();
  for (const [title, , keys] of CATEGORY_GROUPS) {
    for (const key of keys) owners.set(key, { group: title, label: titleCase(key) });
  }
  for (const [title, entries] of BUILTIN) {
    for (const [key, label] of entries) owners.set(key, { group: title, label });
  }

  const placed = new Set<string>();
  const row = (key: string, label: string): ColorRow => {
    placed.add(key);
    return { key, label, hasDefault: hasDefault(key) };
  };
  const groups: ColorGroup[] = [];

  for (const [title, category, builtins] of CATEGORY_GROUPS) {
    const rows = builtins.map((key) => row(key, titleCase(key)));
    const hints: string[] = [];
    for (const value of getCategory(rule, category)) {
      const key = norm(value.name);
      if (key === "" || placed.has(key)) continue;
      const owner = owners.get(key);
      if (owner) {
        if (!builtins.includes(key)) {
          hints.push(
            `"${value.name.trim()}" uses the same colour as ${owner.group} "${owner.label}".`,
          );
        }
        continue;
      }
      placed.add(key);
      rows.push({ key, label: value.name.trim(), hasDefault: hasDefault(key) });
    }
    groups.push({ title, rows, hints });
  }
  for (const [title, entries] of BUILTIN) {
    groups.push({ title, rows: entries.map(([key, label]) => row(key, label)), hints: [] });
  }

  const other = [...new Set([...Object.keys(defaults.light), ...Object.keys(defaults.dark)])]
    .filter((key) => !placed.has(key))
    .sort();
  if (other.length > 0) {
    groups.push({ title: "Other", rows: other.map((key) => row(key, key)), hints: [] });
  }
  return groups;
}
