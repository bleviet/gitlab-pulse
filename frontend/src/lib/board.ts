import { buildPriorityColorMap } from "./colors";
import type { IssueItem, ThemeMode } from "./types";

const DEFAULT_STAGE_ORDER = [
  "Backlog",
  "To Do",
  "In Progress",
  "Review",
  "Testing",
  "Waiting for Release",
  "Done",
  "Closed",
];

function orderedStages(issues: IssueItem[]): string[] {
  if (issues.length === 0) return [];
  const minOrder = new Map<string, number>();
  for (const issue of issues) {
    const stage = issue.stage || "Backlog";
    const current = minOrder.get(stage);
    if (current === undefined || issue.stage_order < current) {
      minOrder.set(stage, issue.stage_order);
    }
  }
  return Array.from(minOrder.keys()).sort((a, b) => {
    const orderA = minOrder.get(a) ?? 999;
    const orderB = minOrder.get(b) ?? 999;
    if (orderA !== orderB) return orderA - orderB;
    const idxA = DEFAULT_STAGE_ORDER.indexOf(a);
    const idxB = DEFAULT_STAGE_ORDER.indexOf(b);
    const fallbackA = idxA >= 0 ? idxA : DEFAULT_STAGE_ORDER.length;
    const fallbackB = idxB >= 0 ? idxB : DEFAULT_STAGE_ORDER.length;
    if (fallbackA !== fallbackB) return fallbackA - fallbackB;
    return a.localeCompare(b);
  });
}

export function getOverviewStages(issues: IssueItem[]): string[] {
  const opened = issues.filter((issue) => issue.state === "opened");
  return orderedStages(opened.length > 0 ? opened : issues);
}

export function getWorkflowStages(issues: IssueItem[]): string[] {
  return orderedStages(issues);
}

export function getBoardLanes(chartStages: string[], filteredIssues: IssueItem[]): string[] {
  const present = orderedStages(filteredIssues);
  const hasChartStage = present.some((stage) => chartStages.includes(stage));
  const lanes = hasChartStage ? [...chartStages] : [];
  for (const stage of present) {
    if (!lanes.includes(stage)) {
      lanes.push(stage);
    }
  }
  return lanes;
}

export function sortIssuesDefault(issues: IssueItem[]): IssueItem[] {
  return [...issues].sort((a, b) => {
    const rankA = a.priority_rank ?? Number.MAX_SAFE_INTEGER;
    const rankB = b.priority_rank ?? Number.MAX_SAFE_INTEGER;
    if (rankA !== rankB) return rankA - rankB;
    return b.days_in_stage - a.days_in_stage;
  });
}

export interface HierarchyRow {
  issue: IssueItem;
  depth: number;
  childCount: number;
}

export function getChildTaskCount(issue: IssueItem, directChildrenCount = 0): number {
  return Math.max(issue.child_ids.length, directChildrenCount);
}

export function sortIssuesHierarchy(issues: IssueItem[]): HierarchyRow[] {
  if (issues.length === 0) return [];
  const byId = new Map<number, IssueItem>();
  const byProjectIid = new Map<string, IssueItem>();
  for (const issue of issues) {
    byId.set(issue.id, issue);
    byProjectIid.set(`${issue.project_id}:${issue.iid}`, issue);
  }

  const resolveParent = (issue: IssueItem): IssueItem | undefined => {
    if (issue.parent_id === null) return undefined;
    const idHit = byId.get(issue.parent_id);
    if (idHit && idHit.id !== issue.id) return idHit;
    const iidHit = byProjectIid.get(`${issue.project_id}:${issue.parent_id}`);
    if (iidHit && iidHit.id !== issue.id) return iidHit;
    return undefined;
  };

  const childrenMap = new Map<number, IssueItem[]>();
  const roots: IssueItem[] = [];
  for (const issue of issues) {
    const parent = resolveParent(issue);
    if (!parent) {
      roots.push(issue);
    } else {
      const list = childrenMap.get(parent.id);
      if (list) {
        list.push(issue);
      } else {
        childrenMap.set(parent.id, [issue]);
      }
    }
  }

  const rows: HierarchyRow[] = [];
  const visited = new Set<number>();

  const dfs = (item: IssueItem, depth: number): void => {
    if (visited.has(item.id)) return;
    visited.add(item.id);
    const children = childrenMap.get(item.id) ?? [];
    rows.push({
      issue: item,
      depth,
      childCount: getChildTaskCount(item, children.length),
    });
    for (const child of children) {
      dfs(child, depth + 1);
    }
  };

  for (const root of roots) {
    dfs(root, 0);
  }
  for (const issue of issues) {
    if (!visited.has(issue.id)) {
      dfs(issue, 0);
    }
  }
  return rows;
}

export interface LanePriorityEntry {
  priority: string;
  count: number;
  color: string;
}

export function computeLanePriorityCounts(
  issues: IssueItem[],
  palette: Record<string, string>,
  priorityOrder: string[],
  theme: ThemeMode,
): Record<string, LanePriorityEntry[]> {
  const colorMap = buildPriorityColorMap(issues, palette, priorityOrder, theme);
  const byStage = new Map<string, Map<string, { count: number; rank: number | null }>>();

  for (const issue of issues) {
    const stage = issue.stage || "Backlog";
    const prio = issue.priority || "Unset";
    let stageMap = byStage.get(stage);
    if (!stageMap) {
      stageMap = new Map();
      byStage.set(stage, stageMap);
    }
    const existing = stageMap.get(prio);
    if (!existing) {
      stageMap.set(prio, { count: 1, rank: issue.priority_rank });
    } else {
      existing.count += 1;
      if (
        issue.priority_rank !== null &&
        (existing.rank === null || issue.priority_rank < existing.rank)
      ) {
        existing.rank = issue.priority_rank;
      }
    }
  }

  const result: Record<string, LanePriorityEntry[]> = {};
  for (const [stage, stageMap] of byStage.entries()) {
    const entries = Array.from(stageMap.entries())
      .sort((a, b) => {
        const aUnset = a[0] === "Unset" ? 1 : 0;
        const bUnset = b[0] === "Unset" ? 1 : 0;
        if (aUnset !== bUnset) return aUnset - bUnset;
        const rankA = a[1].rank ?? Number.MAX_SAFE_INTEGER;
        const rankB = b[1].rank ?? Number.MAX_SAFE_INTEGER;
        if (rankA !== rankB) return rankA - rankB;
        return a[0].localeCompare(b[0]);
      })
      .map(([priority, stat]) => ({
        priority,
        count: stat.count,
        color: colorMap[priority] ?? colorMap.Unset,
      }));
    result[stage] = entries;
  }
  return result;
}
