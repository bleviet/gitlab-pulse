import type { LabelInventoryItem } from "./labelInventory";
import { getCategory, setCategoryValues } from "./ruleDraft";
import { parsePattern, serializePattern } from "./rulePatterns";
import type { MatcherRule, RuleSetBody, SectionId, WorkflowStage } from "./types";

export type SuggestSection = "type" | "impact" | "priority" | "stages";
export type StageKind = "active" | "waiting" | "completed";

export interface Suggestion {
  name: string;
  label: string;
  count: number;
  existingRowIndex: number | null;
  kind?: StageKind;
}

export const SUGGEST_SCOPES: Record<SuggestSection, string[]> = {
  type: ["type", "kind"],
  impact: ["impact", "severity", "sev"],
  priority: ["priority", "prio"],
  stages: ["workflow", "status", "stage", "state"],
};

const IMPACT_RANK: string[][] = [
  ["critical", "blocker"],
  ["high", "major"],
  ["medium", "normal"],
  ["low", "minor", "trivial"],
];

const STAGE_RANK: string[][] = [
  ["backlog", "todo", "to do", "ready", "open"],
  ["design", "architecture", "analysis", "refinement"],
  ["doing", "in progress", "implementation", "development", "dev", "coding"],
  ["review", "mr open"],
  ["test", "testing", "qa", "verify", "validation"],
  ["done", "closed", "released", "complete", "completed"],
];

const COMPLETED = ["done", "closed", "released", "complete", "completed"];
const WAITING = [
  "review",
  "test",
  "testing",
  "qa",
  "verify",
  "validation",
  "blocked",
  "waiting",
  "ready",
  "backlog",
  "todo",
  "to do",
  "open",
];

export function isSuggestSection(section: SectionId): section is SuggestSection {
  return section in SUGGEST_SCOPES;
}

function rankOf(table: string[][], word: string): number {
  const index = table.findIndex((words) => words.includes(word));
  return index === -1 ? table.length : index;
}

function spaced(value: string): string {
  return value.replace(/[-_]+/g, " ").trim().toLowerCase();
}

function displayName(section: SuggestSection, value: string): string {
  if (section === "priority" && /^\d+$/.test(value)) return `P${Number(value)}`;
  return value
    .replace(/[-_]+/g, " ")
    .split(/\s+/)
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

function rowsOf(section: SuggestSection, rule: RuleSetBody): Array<{ name: string; labels: string[] }> {
  return section === "stages" ? rule.workflow.stages : getCategory(rule, section);
}

function isCovered(label: string, rows: Array<{ labels: string[] }>): boolean {
  return rows.some((row) =>
    row.labels.some((raw) => {
      const { mode, value } = parsePattern(raw);
      if (mode === "exact") return value === label;
      if (mode === "contains") return label.includes(value);
      return false;
    }),
  );
}

function stageKind(value: string): StageKind {
  const word = spaced(value);
  if (COMPLETED.includes(word)) return "completed";
  if (WAITING.includes(word)) return "waiting";
  return "active";
}

function compare(section: SuggestSection, a: Suggestion, b: Suggestion): number {
  const wa = spaced(a.name);
  const wb = spaced(b.name);
  if (section === "impact") {
    return rankOf(IMPACT_RANK, wa) - rankOf(IMPACT_RANK, wb) || a.name.localeCompare(b.name);
  }
  if (section === "stages") {
    return rankOf(STAGE_RANK, wa) - rankOf(STAGE_RANK, wb) || a.name.localeCompare(b.name);
  }
  if (section === "priority") {
    const na = /^p\d+$/i.test(a.name) ? Number(a.name.slice(1)) : null;
    const nb = /^p\d+$/i.test(b.name) ? Number(b.name.slice(1)) : null;
    if (na !== null || nb !== null) {
      if (na === null) return 1;
      if (nb === null) return -1;
      return na - nb;
    }
    return rankOf(IMPACT_RANK, wa) - rankOf(IMPACT_RANK, wb) || a.name.localeCompare(b.name);
  }
  return a.name.localeCompare(b.name);
}

export function suggestRows(
  section: SuggestSection,
  rule: RuleSetBody,
  inventory: LabelInventoryItem[],
): Suggestion[] {
  const rows = rowsOf(section, rule);
  const scopes = SUGGEST_SCOPES[section];
  const suggestions: Suggestion[] = [];
  for (const item of inventory) {
    const at = item.name.indexOf("::");
    if (at <= 0) continue;
    const value = item.name.slice(at + 2);
    if (!scopes.includes(item.name.slice(0, at).toLowerCase()) || value === "") continue;
    if (isCovered(item.name, rows)) continue;
    const name = displayName(section, value);
    if (item.count === 0 || name === "") continue;
    if (section === "stages" && name.toLowerCase() === "backlog") continue;
    const existing = rows.findIndex((r) => r.name.trim().toLowerCase() === name.toLowerCase());
    suggestions.push({
      name,
      label: item.name,
      count: item.count,
      existingRowIndex: existing === -1 ? null : existing,
      ...(section === "stages" ? { kind: stageKind(value) } : {}),
    });
  }
  return suggestions.sort((a, b) => compare(section, a, b));
}

export function applySuggestions(
  section: SuggestSection,
  rule: RuleSetBody,
  chosen: Suggestion[],
): RuleSetBody {
  const rows: Array<MatcherRule | WorkflowStage> = [...rowsOf(section, rule)] as Array<
    MatcherRule | WorkflowStage
  >;
  for (const suggestion of chosen) {
    const pattern = serializePattern({ mode: "exact", value: suggestion.label });
    let index = rows.findIndex((r) => r.name.trim().toLowerCase() === suggestion.name.toLowerCase());
    if (index === -1) {
      rows.push(
        section === "stages"
          ? { name: suggestion.name, labels: [], type: suggestion.kind ?? "active", description: "" }
          : { name: suggestion.name, labels: [], title: [] },
      );
      index = rows.length - 1;
    }
    const target = rows[index];
    if (!target.labels.includes(pattern)) {
      rows[index] = { ...target, labels: [...target.labels, pattern] };
    }
  }
  if (section === "stages") {
    return { ...rule, workflow: { ...rule.workflow, stages: rows as WorkflowStage[] } };
  }
  return setCategoryValues(rule, section, rows as MatcherRule[]);
}
