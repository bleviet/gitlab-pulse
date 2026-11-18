import type { IssueItem } from "./types";

export function normalizeSearchText(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (Array.isArray(value)) {
    return value
      .map((item) => normalizeSearchText(item))
      .filter(Boolean)
      .join(" ");
  }
  return String(value)
    .replaceAll("_", " ")
    .replaceAll("::", " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

function lcsLength(a: string, b: string): number {
  const m = a.length;
  const n = b.length;
  if (m === 0 || n === 0) return 0;
  let prev = new Array<number>(n + 1).fill(0);
  let curr = new Array<number>(n + 1).fill(0);
  for (let i = 1; i <= m; i += 1) {
    const chA = a[i - 1];
    for (let j = 1; j <= n; j += 1) {
      if (chA === b[j - 1]) {
        curr[j] = prev[j - 1] + 1;
      } else {
        curr[j] = curr[j - 1] > prev[j] ? curr[j - 1] : prev[j];
      }
    }
    const tmp = prev;
    prev = curr;
    curr = tmp;
    curr.fill(0);
  }
  return prev[n];
}

export function similarityRatio(a: string, b: string): number {
  if (!a && !b) return 1;
  if (!a || !b) return 0;
  return (2 * lcsLength(a, b)) / (a.length + b.length);
}

function searchThreshold(normalizedQuery: string): number {
  const len = normalizedQuery.length;
  if (len <= 4) return 0.9;
  if (len <= 8) return 0.82;
  return 0.72;
}

function issueCells(issue: IssueItem): string[] {
  return [
    normalizeSearchText(issue.iid),
    normalizeSearchText(issue.title),
    normalizeSearchText(issue.stage),
    normalizeSearchText(issue.days_in_stage),
    normalizeSearchText(issue.priority || "Unset"),
    normalizeSearchText(issue.contexts),
    normalizeSearchText(issue.milestone),
    normalizeSearchText(issue.assignee),
  ];
}

function isFuzzyCellMatch(cell: string, normalizedQuery: string, threshold: number): boolean {
  if (!cell) return false;
  if (cell.includes(normalizedQuery)) return true;
  let best = similarityRatio(normalizedQuery, cell);
  for (const token of cell.split(" ")) {
    const score = similarityRatio(normalizedQuery, token);
    if (score > best) best = score;
  }
  return best >= threshold;
}

export function filterIssuesBySearch(issues: IssueItem[], query: string): IssueItem[] {
  const normalizedQuery = normalizeSearchText(query);
  if (!normalizedQuery) {
    return issues;
  }
  const tokens = normalizedQuery.split(" ").filter(Boolean);
  if (tokens.length === 0) {
    return issues;
  }

  const cellsPerIssue = issues.map((issue) => ({
    issue,
    cells: issueCells(issue),
  }));

  const exactMatches: IssueItem[] = [];
  for (const entry of cellsPerIssue) {
    const rowText = entry.cells.filter(Boolean).join(" ");
    if (tokens.every((token) => rowText.includes(token))) {
      exactMatches.push(entry.issue);
    }
  }

  if (exactMatches.length > 0) {
    return exactMatches;
  }

  const threshold = searchThreshold(normalizedQuery);
  return cellsPerIssue
    .filter((entry) => entry.cells.some((cell) => isFuzzyCellMatch(cell, normalizedQuery, threshold)))
    .map((entry) => entry.issue);
}
