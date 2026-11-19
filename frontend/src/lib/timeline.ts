import { buildIssueTypeDonutData } from "./analytics";
import { buildPriorityColorMap } from "./colors";
import type { IssueItem, ThemeMode } from "./types";

export type MilestoneStatus = "Complete" | "Incomplete" | "On Track" | "Overdue";

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
  /** Dated milestones hidden before the one-year window. */
  hiddenEarlierCount: number;
  /** Dated milestones hidden after the one-year window. */
  hiddenLaterCount: number;
  /** Dated milestones outside the one-year window, in either mode. */
  outOfWindowCount: number;
}

const DAY_MS = 86_400_000;
const WINDOW_BEFORE_MS = 182 * DAY_MS;
const WINDOW_AFTER_MS = 183 * DAY_MS;

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

/**
 * Builds the release rail model for milestones with a due date.
 *
 * By default the scale covers a one-year window around now and milestones
 * outside it are counted instead of placed. The highlighted milestone always
 * stays visible and widens the window if needed. With showAll the scale fits
 * every dated milestone.
 *
 * @param issues Issues before the milestone filter is applied.
 * @param palette Resolved palette used for status colors.
 * @param highlightMilestone Title of the selected milestone, if any.
 * @param now Reference instant for status and the window.
 * @param showAll Fit the scale to every dated milestone.
 * @returns The rail model, or null when no milestone has a due date.
 */
export function buildMilestoneTimelineData(
  issues: IssueItem[],
  palette: Record<string, string>,
  highlightMilestone: string | null,
  now: Date = new Date(),
  showAll = false,
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
  };

  interface RawPoint {
    title: string;
    status: MilestoneStatus;
    color: string;
    dueDateIso: string | null;
    dueDateMs: number;
    closedCount: number;
    totalCount: number;
  }

  const dated: RawPoint[] = [];

  for (const entry of grouped.values()) {
    if (entry.dueDateMs === null) {
      continue;
    }
    let status: MilestoneStatus;
    if (entry.allClosed) {
      status = entry.totalCount > 0 && entry.closedCount === entry.totalCount ? "Complete" : "Incomplete";
    } else if (entry.dueDateMs < nowMs) {
      status = "Overdue";
    } else {
      status = "On Track";
    }

    dated.push({
      title: entry.title,
      status,
      color: statusColor[status],
      dueDateIso: entry.dueDateIso,
      dueDateMs: entry.dueDateMs,
      closedCount: entry.closedCount,
      totalCount: entry.totalCount,
    });
  }

  if (dated.length === 0) {
    return null;
  }

  const hasHighlight = Boolean(highlightMilestone && highlightMilestone !== "All");
  const windowMin = nowMs - WINDOW_BEFORE_MS;
  const windowMax = nowMs + WINDOW_AFTER_MS;
  const isEarlier = (p: RawPoint): boolean => p.dueDateMs < windowMin;
  const isLater = (p: RawPoint): boolean => p.dueDateMs > windowMax;
  const outOfWindowCount = dated.filter((p) => isEarlier(p) || isLater(p)).length;

  let visible = dated;
  let minTimeMs: number;
  let maxTimeMs: number;
  let hiddenEarlierCount = 0;
  let hiddenLaterCount = 0;
  if (showAll) {
    const latestDue = dated.reduce((max, p) => Math.max(max, p.dueDateMs), nowMs + 90 * DAY_MS);
    maxTimeMs = Math.max(nowMs + 90 * DAY_MS, latestDue);
    const earliestDated = dated.reduce((min, p) => Math.min(min, p.dueDateMs), nowMs - 270 * DAY_MS);
    minTimeMs = Math.min(nowMs - 270 * DAY_MS, earliestDated - 14 * DAY_MS);
  } else {
    const isPinned = (p: RawPoint): boolean => hasHighlight && p.title === highlightMilestone;
    visible = dated.filter((p) => isPinned(p) || (!isEarlier(p) && !isLater(p)));
    hiddenEarlierCount = dated.filter((p) => !isPinned(p) && isEarlier(p)).length;
    hiddenLaterCount = dated.filter((p) => !isPinned(p) && isLater(p)).length;
    minTimeMs = visible.reduce((min, p) => Math.min(min, p.dueDateMs), windowMin);
    maxTimeMs = visible.reduce((max, p) => Math.max(max, p.dueDateMs), windowMax);
  }

  const combined = visible
    .map((p) => ({ ...p, plotTimeMs: p.dueDateMs }))
    .sort((a, b) => a.plotTimeMs - b.plotTimeMs);

  const points: MilestonePoint[] = combined.map((p, idx) => {
    const isHighlighted = hasHighlight && p.title === highlightMilestone;
    return {
      title: p.title,
      status: p.status,
      color: p.color,
      dueDateIso: p.dueDateIso,
      dueDateLabel: p.dueDateIso ?? "",
      plotTimeMs: p.plotTimeMs,
      laneY: idx % 2 === 0 ? 1 : -1,
      closedCount: p.closedCount,
      totalCount: p.totalCount,
      isHighlighted,
      isDimmed: hasHighlight && !isHighlighted,
    };
  });

  return {
    points,
    minTimeMs,
    maxTimeMs,
    nowTimeMs: nowMs,
    hiddenEarlierCount,
    hiddenLaterCount,
    outOfWindowCount,
  };
}

function formatMonthTick(ms: number): string {
  return new Date(ms).toLocaleDateString("en-US", {
    month: "short",
    year: "2-digit",
    timeZone: "UTC",
  });
}

/**
 * Builds axis ticks on UTC month starts.
 *
 * Ticks step every k months, with the smallest k that keeps the count within
 * maxCount.
 *
 * @param minMs Start of the visible range in epoch milliseconds.
 * @param maxMs End of the visible range in epoch milliseconds.
 * @param maxCount Maximum number of ticks to return.
 * @returns Tick instants with short month labels.
 */
export function buildMonthTicks(
  minMs: number,
  maxMs: number,
  maxCount: number,
): Array<{ ms: number; label: string }> {
  const start = new Date(minMs);
  const year = start.getUTCFullYear();
  let month = start.getUTCMonth();
  if (Date.UTC(year, month, 1) < minMs) {
    month += 1;
  }
  const starts: number[] = [];
  for (let ms = Date.UTC(year, month, 1); ms <= maxMs; ms = Date.UTC(year, month, 1)) {
    starts.push(ms);
    month += 1;
  }
  const step = Math.max(1, Math.ceil(starts.length / Math.max(maxCount, 1)));
  return starts
    .filter((_, idx) => idx % step === 0)
    .map((ms) => ({ ms, label: formatMonthTick(ms) }));
}

export interface UnscheduledSegment {
  label: string;
  count: number;
  color: string;
}

export interface UnscheduledMilestoneRow {
  title: string;
  openCount: number;
  totalCount: number;
  oldestOpenDays: number;
  byPriority: UnscheduledSegment[];
  byType: UnscheduledSegment[];
}

export interface UnscheduledModel {
  rows: UnscheduledMilestoneRow[];
  openIssueCount: number;
  hiddenClosedCount: number;
  priorityLegend: UnscheduledSegment[];
  typeLegend: UnscheduledSegment[];
}

/**
 * Picks the rows to show, keeping the selected milestone visible.
 *
 * Takes the first maxRows rows. If the active milestone is a later row, it
 * replaces the last visible row.
 *
 * @param rows Rows in display order.
 * @param activeMilestone Title of the selected milestone, if any.
 * @param maxRows Maximum number of rows to return.
 * @returns The visible rows in display order.
 */
export function selectVisibleUnscheduledRows(
  rows: UnscheduledMilestoneRow[],
  activeMilestone: string | null,
  maxRows: number,
): UnscheduledMilestoneRow[] {
  const visible = rows.slice(0, maxRows);
  const active = rows.slice(maxRows).find((row) => row.title === activeMilestone);
  if (active && visible.length > 0) {
    visible[visible.length - 1] = active;
  }
  return visible;
}

function countSegments(
  labels: string[],
  order: string[],
  colors: Record<string, string>,
): UnscheduledSegment[] {
  const counts = new Map<string, number>();
  for (const label of labels) {
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  return order
    .filter((label) => (counts.get(label) ?? 0) > 0)
    .map((label) => ({ label, count: counts.get(label) ?? 0, color: colors[label] }));
}

function sumSegments(rowSegments: UnscheduledSegment[][], order: string[]): UnscheduledSegment[] {
  const totals = new Map<string, UnscheduledSegment>();
  for (const segments of rowSegments) {
    for (const seg of segments) {
      const existing = totals.get(seg.label);
      if (existing) {
        existing.count += seg.count;
      } else {
        totals.set(seg.label, { ...seg });
      }
    }
  }
  return order.flatMap((label) => {
    const seg = totals.get(label);
    return seg ? [seg] : [];
  });
}

/**
 * Summarizes milestones that have no due date, using open issues only.
 *
 * A milestone is unscheduled when none of its issues carries a parseable due
 * date. Unscheduled milestones without open issues are counted, not listed.
 *
 * @param issues Issues before the milestone filter is applied.
 * @param palette Resolved palette used for priority and type colors.
 * @param priorityOrder Priority labels in display order.
 * @param theme Active theme, used for fallback colors.
 * @returns Rows sorted by open issue count plus legends and totals.
 */
export function buildUnscheduledMilestonesData(
  issues: IssueItem[],
  palette: Record<string, string>,
  priorityOrder: string[],
  theme: ThemeMode,
): UnscheduledModel {
  const groups = new Map<string, { dated: boolean; issues: IssueItem[] }>();
  for (const issue of issues) {
    if (!issue.milestone) continue;
    let group = groups.get(issue.milestone);
    if (!group) {
      group = { dated: false, issues: [] };
      groups.set(issue.milestone, group);
    }
    group.issues.push(issue);
    if (issue.milestone_due_date && !Number.isNaN(Date.parse(issue.milestone_due_date))) {
      group.dated = true;
    }
  }

  const priorityColors = buildPriorityColorMap(issues, palette, priorityOrder, theme);
  const priorityKeys = Object.keys(priorityColors);
  const priorityLabelOrder = [...priorityKeys.filter((k) => k !== "Unset"), "Unset"];

  const openGroups: Array<{ title: string; all: IssueItem[]; open: IssueItem[] }> = [];
  let hiddenClosedCount = 0;
  for (const [title, group] of groups) {
    if (group.dated) continue;
    const open = group.issues.filter((issue) => issue.state === "opened");
    if (open.length === 0) {
      hiddenClosedCount += 1;
    } else {
      openGroups.push({ title, all: group.issues, open });
    }
  }

  const allOpen = openGroups.flatMap((g) => g.open);
  const typeSlices = buildIssueTypeDonutData(allOpen, "opened", palette, theme).slices;
  const typeLabelOrder = typeSlices.map((s) => s.label);
  const typeColors = Object.fromEntries(typeSlices.map((s) => [s.label, s.color]));

  const rows: UnscheduledMilestoneRow[] = openGroups
    .map((g) => ({
      title: g.title,
      openCount: g.open.length,
      totalCount: g.all.length,
      oldestOpenDays: g.open.reduce((max, issue) => Math.max(max, issue.age_days), 0),
      byPriority: countSegments(
        g.open.map((issue) => issue.priority || "Unset"),
        priorityLabelOrder,
        priorityColors,
      ),
      byType: countSegments(
        g.open.map((issue) => (issue.issue_type || "Unset").trim() || "Unset"),
        typeLabelOrder,
        typeColors,
      ),
    }))
    .sort((a, b) => b.openCount - a.openCount || naturalCompare(a.title, b.title));

  return {
    rows,
    openIssueCount: rows.reduce((sum, row) => sum + row.openCount, 0),
    hiddenClosedCount,
    priorityLegend: sumSegments(rows.map((r) => r.byPriority), priorityLabelOrder),
    typeLegend: sumSegments(rows.map((r) => r.byType), typeLabelOrder),
  };
}
