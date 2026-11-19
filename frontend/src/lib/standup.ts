import type { IssueItem } from "./types";

export type CoveredFilterMode = "all" | "remaining" | "covered";

export interface StandupState {
  date: string;
  coveredIds: number[];
  activeId: number | null;
}

export const STANDUP_STORAGE_KEY = "pulse_standup_today";

export function getLocalDateKey(now: Date = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function createEmptyStandupState(today: string = getLocalDateKey()): StandupState {
  return {
    date: today,
    coveredIds: [],
    activeId: null,
  };
}

export function parseStandupState(
  raw: string | null,
  today: string = getLocalDateKey(),
): StandupState {
  if (!raw) {
    return createEmptyStandupState(today);
  }
  try {
    const parsed: unknown = JSON.parse(raw);
    if (typeof parsed !== "object" || parsed === null) {
      return createEmptyStandupState(today);
    }
    const candidate = parsed as Partial<StandupState>;
    if (candidate.date !== today || !Array.isArray(candidate.coveredIds)) {
      return createEmptyStandupState(today);
    }
    const seen = new Set<number>();
    const coveredIds: number[] = [];
    for (const item of candidate.coveredIds) {
      if (typeof item === "number" && Number.isFinite(item) && !seen.has(item)) {
        seen.add(item);
        coveredIds.push(item);
      }
    }
    const activeId =
      typeof candidate.activeId === "number" && Number.isFinite(candidate.activeId)
        ? candidate.activeId
        : null;
    return {
      date: today,
      coveredIds,
      activeId,
    };
  } catch {
    return createEmptyStandupState(today);
  }
}

export function markIssueOpened(
  state: StandupState,
  issueId: number,
  today: string = getLocalDateKey(),
): StandupState {
  const base = state.date === today ? state : createEmptyStandupState(today);
  const coveredIds = base.coveredIds.includes(issueId)
    ? base.coveredIds
    : [...base.coveredIds, issueId];
  return {
    date: today,
    coveredIds,
    activeId: issueId,
  };
}

export function toggleIssueCovered(
  state: StandupState,
  issueId: number,
  today: string = getLocalDateKey(),
): StandupState {
  const base = state.date === today ? state : createEmptyStandupState(today);
  const isCovered = base.coveredIds.includes(issueId);
  if (isCovered) {
    return {
      date: today,
      coveredIds: base.coveredIds.filter((id) => id !== issueId),
      activeId: base.activeId === issueId ? null : base.activeId,
    };
  }
  return {
    date: today,
    coveredIds: [...base.coveredIds, issueId],
    activeId: base.activeId,
  };
}

export function filterIssuesByCoverage(
  issues: IssueItem[],
  coveredSet: ReadonlySet<number>,
  mode: CoveredFilterMode,
): IssueItem[] {
  if (mode === "remaining") {
    return issues.filter((issue) => !coveredSet.has(issue.id));
  }
  if (mode === "covered") {
    return issues.filter((issue) => coveredSet.has(issue.id));
  }
  return issues;
}

export function nextCoveredFilterMode(current: CoveredFilterMode): CoveredFilterMode {
  if (current === "all") return "remaining";
  if (current === "remaining") return "covered";
  return "all";
}
