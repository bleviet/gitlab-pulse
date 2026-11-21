import type { CountChange, ImpactSummary, RuleProblem, SectionId } from "./types";

export interface ImpactRow {
  key: string;
  label: string;
  before: number;
  after: number;
  delta: number;
}

export interface ImpactGroup {
  title: string;
  rows: ImpactRow[];
}

const QUALITY_LABELS: Record<string, string> = {
  STALE: "Stale",
  MISSING_LABEL: "Missing a required label",
  MISSING_FIELD: "Missing a required field",
  CONFLICTING_LABELS: "More than one type label",
  ORPHAN_TASK: "Task whose parent does not exist",
  EXCEEDS_CYCLE_TIME: "Over the cycle time limit",
  MISSING_CONTEXT: "Belongs to no context",
};

function toRows(
  changes: CountChange[],
  labelFor: (name: string | null) => string,
): ImpactRow[] {
  return changes.map((change, i) => ({
    key: `${change.name ?? "none"}:${i}`,
    label: labelFor(change.name),
    before: change.before,
    after: change.after,
    delta: change.after - change.before,
  }));
}

function named(empty: string): (name: string | null) => string {
  return (name) => name ?? empty;
}

export function groupsForSection(section: SectionId, impact: ImpactSummary): ImpactGroup[] {
  switch (section) {
    case "type":
      return [{ title: "Issues by type", rows: toRows(impact.types, named("No type")) }];
    case "severity":
      return [
        { title: "Issues by severity", rows: toRows(impact.severities, named("No severity")) },
      ];
    case "priority":
      return [
        { title: "Issues by priority", rows: toRows(impact.priorities, named("No priority")) },
      ];
    case "stages":
      return [{ title: "Issues by stage", rows: toRows(impact.stages, named("No stage")) }];
    case "contexts":
      return [
        { title: "Issues by context", rows: toRows(impact.contexts, named("No context")) },
      ];
    case "colors":
      return [];
    case "projects":
    case "history":
    case "text":
      return OVERVIEW_SECTIONS.flatMap((id) => groupsForSection(id, impact));
    case "quality":
      return [
        {
          title: "Issues flagged",
          rows: toRows(impact.quality, (name) =>
            name === null ? "No flag" : (QUALITY_LABELS[name] ?? name),
          ),
        },
      ];
  }
}

export function formatDelta(delta: number): string {
  if (delta > 0) return `+${delta}`;
  if (delta < 0) return `−${Math.abs(delta)}`;
  return "";
}

export function mergeProblems(...lists: RuleProblem[][]): RuleProblem[] {
  const seen = new Set<string>();
  const merged: RuleProblem[] = [];
  for (const problem of lists.flat()) {
    if (seen.has(problem.path)) continue;
    seen.add(problem.path);
    merged.push(problem);
  }
  return merged;
}

const OVERVIEW_SECTIONS: SectionId[] = [
  "type",
  "severity",
  "priority",
  "stages",
  "contexts",
  "quality",
];

export function changedGroups(impact: ImpactSummary): ImpactGroup[] {
  const result: ImpactGroup[] = [];
  for (const section of OVERVIEW_SECTIONS) {
    for (const group of groupsForSection(section, impact)) {
      if (!group.rows.some((row) => row.delta !== 0)) continue;
      const changed = group.rows.filter((row) => row.delta !== 0);
      const rest = group.rows.filter((row) => row.delta === 0);
      result.push({ title: group.title, rows: [...changed, ...rest] });
    }
  }
  return result;
}
