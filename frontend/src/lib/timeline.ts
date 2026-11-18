import type { IssueItem } from "./types";

export type MilestoneStatus = "Complete" | "Incomplete" | "On Track" | "Overdue" | "Unscheduled";

export interface MilestonePoint {
  title: string;
  status: MilestoneStatus;
  color: string;
  dueDateIso: string | null;
  dueDateLabel: string;
  plotTimeMs: number;
  laneY: 1 | -1;
  closedCount: number;
  totalCount: number;
  isHighlighted: boolean;
  isDimmed: boolean;
}

export interface TimelineModel {
  points: MilestonePoint[];
  minTimeMs: number;
  maxTimeMs: number;
  nowTimeMs: number;
  separatorTimeMs: number | null;
}

const DAY_MS = 86_400_000;
const UNDATED_GAP_MS = 30 * DAY_MS;
const UNDATED_STEP_MS = 21 * DAY_MS;

export function naturalCompare(a: string, b: string): number {
  const partsA = a.split(/(\d+)/).filter(Boolean);
  const partsB = b.split(/(\d+)/).filter(Boolean);
  const len = Math.max(partsA.length, partsB.length);
  for (let i = 0; i < len; i += 1) {
    const segA = partsA[i];
    const segB = partsB[i];
    if (segA === undefined) return -1;
    if (segB === undefined) return 1;
    const isNumA = /^\d+$/.test(segA);
    const isNumB = /^\d+$/.test(segB);
    if (isNumA && isNumB) {
      const diff = Number.parseInt(segA, 10) - Number.parseInt(segB, 10);
      if (diff !== 0) return diff;
    } else if (isNumA !== isNumB) {
      return isNumA ? -1 : 1;
    } else if (segA !== segB) {
      return segA < segB ? -1 : 1;
    }
  }
  return 0;
}

export function buildMilestoneTimelineData(
  issues: IssueItem[],
  palette: Record<string, string>,
  highlightMilestone: string | null,
  now: Date = new Date(),
): TimelineModel | null {
  const grouped = new Map<
    string,
    {
      title: string;
      dueDateIso: string | null;
      dueDateMs: number | null;
      allClosed: boolean;
      totalCount: number;
      closedCount: number;
    }
  >();

  for (const issue of issues) {
    if (!issue.milestone) continue;
    let entry = grouped.get(issue.milestone);
    if (!entry) {
      const dueMs = issue.milestone_due_date ? Date.parse(issue.milestone_due_date) : null;
      entry = {
        title: issue.milestone,
        dueDateIso: issue.milestone_due_date ? issue.milestone_due_date.slice(0, 10) : null,
        dueDateMs: dueMs !== null && !Number.isNaN(dueMs) ? dueMs : null,
        allClosed: true,
        totalCount: 0,
        closedCount: 0,
      };
      grouped.set(issue.milestone, entry);
    } else if (entry.dueDateMs === null && issue.milestone_due_date) {
      const dueMs = Date.parse(issue.milestone_due_date);
      if (!Number.isNaN(dueMs)) {
        entry.dueDateMs = dueMs;
        entry.dueDateIso = issue.milestone_due_date.slice(0, 10);
      }
    }
    entry.totalCount += 1;
    if (issue.state === "closed") {
      entry.closedCount += 1;
    } else {
      entry.allClosed = false;
    }
  }

  const nowMs = now.getTime();
  const statusColor: Record<MilestoneStatus, string> = {
    Complete: palette.ms_complete ?? "#00f2fe",
    Incomplete: palette.ms_incomplete ?? "#f4a44a",
    "On Track": palette.ms_on_track ?? "#56d4b0",
    Overdue: palette.ms_overdue ?? "#f5576c",
    Unscheduled: palette.neutral ?? "#7a8fa8",
  };

  interface RawPoint {
    title: string;
    status: MilestoneStatus;
    color: string;
    dueDateIso: string | null;
    dueDateMs: number | null;
    closedCount: number;
    totalCount: number;
  }

  const dated: RawPoint[] = [];
  const undated: RawPoint[] = [];

  for (const entry of grouped.values()) {
    const isUndated = entry.dueDateMs === null;
    if (isUndated && entry.allClosed) {
      continue;
    }
    let status: MilestoneStatus;
    if (isUndated) {
      status = "Unscheduled";
    } else if (entry.allClosed) {
      status = entry.totalCount > 0 && entry.closedCount === entry.totalCount ? "Complete" : "Incomplete";
    } else if ((entry.dueDateMs as number) < nowMs) {
      status = "Overdue";
    } else {
      status = "On Track";
    }

    const point: RawPoint = {
      title: entry.title,
      status,
      color: statusColor[status],
      dueDateIso: entry.dueDateIso,
      dueDateMs: entry.dueDateMs,
      closedCount: entry.closedCount,
      totalCount: entry.totalCount,
    };
    if (isUndated) {
      undated.push(point);
    } else {
      dated.push(point);
    }
  }

  if (dated.length === 0 && undated.length === 0) {
    return null;
  }

  const latestDue = dated.reduce((max, p) => Math.max(max, p.dueDateMs ?? 0), nowMs + 90 * DAY_MS);
  const windowEnd = Math.max(nowMs + 90 * DAY_MS, latestDue);
  let separatorTimeMs: number | null = null;
  let maxTimeMs = windowEnd;

  const combined: Array<RawPoint & { plotTimeMs: number }> = dated.map((p) => ({
    ...p,
    plotTimeMs: p.dueDateMs as number,
  }));

  if (undated.length > 0) {
    undated.sort((a, b) => naturalCompare(a.title, b.title));
    separatorTimeMs = windowEnd + UNDATED_GAP_MS / 2;
    undated.forEach((p, idx) => {
      const plotTimeMs = windowEnd + UNDATED_GAP_MS + idx * UNDATED_STEP_MS;
      combined.push({ ...p, plotTimeMs });
      if (plotTimeMs > maxTimeMs) {
        maxTimeMs = plotTimeMs;
      }
    });
    maxTimeMs += UNDATED_GAP_MS / 2;
  }

  combined.sort((a, b) => a.plotTimeMs - b.plotTimeMs);

  const hasHighlight = Boolean(highlightMilestone && highlightMilestone !== "All");
  const points: MilestonePoint[] = combined.map((p, idx) => {
    const isHighlighted = hasHighlight && p.title === highlightMilestone;
    return {
      title: p.title,
      status: p.status,
      color: p.color,
      dueDateIso: p.dueDateIso,
      dueDateLabel: p.dueDateIso ?? "Not set",
      plotTimeMs: p.plotTimeMs,
      laneY: idx % 2 === 0 ? 1 : -1,
      closedCount: p.closedCount,
      totalCount: p.totalCount,
      isHighlighted,
      isDimmed: hasHighlight && !isHighlighted,
    };
  });

  const earliestDated = dated.reduce((min, p) => Math.min(min, p.dueDateMs ?? min), nowMs - 270 * DAY_MS);
  const minTimeMs = Math.min(nowMs - 270 * DAY_MS, earliestDated - 14 * DAY_MS);

  return {
    points,
    minTimeMs,
    maxTimeMs,
    nowTimeMs: nowMs,
    separatorTimeMs,
  };
}
