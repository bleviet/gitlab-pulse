import type { IssueItem, RuleSetItem } from "./types";

export interface ProjectInfo {
  id: number;
  name: string;
  count: number;
}

const URL_MARKERS = ["/-/issues/", "/issues/"];

function nameFromUrl(url: string | null): string | null {
  if (!url) return null;
  let pathname: string;
  try {
    pathname = new URL(url).pathname;
  } catch {
    return null;
  }
  for (const marker of URL_MARKERS) {
    const at = pathname.indexOf(marker);
    if (at > 1) return pathname.slice(1, at);
  }
  return null;
}

export function projectLabel(id: number, inventory: ProjectInfo[]): string {
  return inventory.find((p) => p.id === id)?.name ?? `Project ${id}`;
}

function byName(a: ProjectInfo, b: ProjectInfo): number {
  return a.name.localeCompare(b.name) || a.id - b.id;
}

export function buildProjectInventory(issues: IssueItem[]): ProjectInfo[] {
  const found = new Map<number, { count: number; name: string | null }>();
  for (const issue of issues) {
    const entry = found.get(issue.project_id) ?? { count: 0, name: null };
    entry.count += 1;
    entry.name ??= nameFromUrl(issue.web_url);
    found.set(issue.project_id, entry);
  }
  return [...found.entries()]
    .map(([id, entry]) => ({ id, name: entry.name ?? `Project ${id}`, count: entry.count }))
    .sort(byName);
}

export function knownProjects(
  inventory: ProjectInfo[],
  ruleSets: RuleSetItem[],
  extraIds: number[],
): ProjectInfo[] {
  const known = new Map(inventory.map((p) => [p.id, p]));
  const ids = [...ruleSets.flatMap((r) => r.rule.project_ids), ...extraIds];
  for (const id of ids) {
    if (!known.has(id)) known.set(id, { id, name: projectLabel(id, inventory), count: 0 });
  }
  return [...known.values()].sort(byName);
}
