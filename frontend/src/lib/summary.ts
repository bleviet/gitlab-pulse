import { buildPriorityColorMap } from "./colors";
import { isRecentIssue, RECENT_DAYS } from "./facets";
import type { IssueFacets, IssueItem, ThemeMode } from "./types";

export interface SummaryItem {
  itemId: string;
  label: string;
  value: number;
  icon: "circle" | "plus" | "check" | "milestone" | "user-x" | "tag" | "";
  dotColor?: string;
  facets: IssueFacets;
}

export interface SummaryGroup {
  heading: string;
  items: SummaryItem[];
}

const HINT_ITEMS: Array<{
  code: string;
  label: string;
  icon: "milestone" | "user-x" | "tag";
}> = [
  { code: "MISSING_MILESTONE", label: "No milestone", icon: "milestone" },
  { code: "UNASSIGNED_OWNER", label: "Unassigned", icon: "user-x" },
  { code: "MIXED_CLASSIFICATION", label: "Mixed", icon: "tag" },
];

export function buildSummaryGroups(
  issues: IssueItem[],
  palette: Record<string, string>,
  priorityOrder: string[],
  theme: ThemeMode,
  now: Date = new Date(),
): SummaryGroup[] {
  const opened = issues.filter((issue) => issue.state === "opened");
  const newRecent = issues.filter((issue) => isRecentIssue(issue, "created", now)).length;
  const closedRecent = issues.filter((issue) => isRecentIssue(issue, "closed", now)).length;

  const flow: SummaryItem[] = [
    {
      itemId: "open",
      label: "Open",
      value: opened.length,
      icon: "circle",
      facets: { state: "opened" },
    },
    {
      itemId: "new_recent",
      label: `New ${RECENT_DAYS}d`,
      value: newRecent,
      icon: "plus",
      facets: { state: "all", recent: "created" },
    },
    {
      itemId: "closed_recent",
      label: `Closed ${RECENT_DAYS}d`,
      value: closedRecent,
      icon: "check",
      facets: { state: "closed", recent: "closed" },
    },
  ];

  const colorMap = buildPriorityColorMap(issues, palette, priorityOrder, theme);
  const stats = new Map<string, { count: number; rank: number | null }>();
  for (const issue of opened) {
    const label = issue.priority || "Unset";
    const prev = stats.get(label);
    if (!prev) {
      stats.set(label, { count: 1, rank: issue.priority_rank });
    } else {
      prev.count += 1;
      if (
        issue.priority_rank !== null &&
        (prev.rank === null || issue.priority_rank < prev.rank)
      ) {
        prev.rank = issue.priority_rank;
      }
    }
  }

  const orderedPriorities = Array.from(stats.entries()).sort((a, b) => {
    const aUnset = a[0] === "Unset" ? 1 : 0;
    const bUnset = b[0] === "Unset" ? 1 : 0;
    if (aUnset !== bUnset) return aUnset - bUnset;
    const rankA = a[1].rank ?? Number.MAX_SAFE_INTEGER;
    const rankB = b[1].rank ?? Number.MAX_SAFE_INTEGER;
    if (rankA !== rankB) return rankA - rankB;
    return a[0].localeCompare(b[0]);
  });

  const priorities: SummaryItem[] = orderedPriorities.map(([label, stat]) => ({
    itemId: `priority_${label}`,
    label,
    value: stat.count,
    icon: "",
    dotColor: colorMap[label] ?? colorMap.Unset,
    facets: { state: "opened", priority: label },
  }));

  const hints: SummaryItem[] = HINT_ITEMS.map(({ code, label, icon }) => ({
    itemId: `hint_${code.toLowerCase()}`,
    label,
    value: opened.filter((issue) => issue.quality_signals.includes(code)).length,
    icon,
    facets: { signal: code },
  }));

  return [
    { heading: "Flow", items: flow },
    { heading: "Open by priority", items: priorities },
    { heading: "Hints", items: hints },
  ];
}
