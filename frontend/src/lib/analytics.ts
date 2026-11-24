import { buildPriorityColorMap, getIssueTypeColor } from "./colors";
import type { IssueItem, ThemeMode } from "./types";

export interface DonutSlice {
  label: string;
  count: number;
  color: string;
}

export interface DonutModel {
  total: number;
  slices: DonutSlice[];
}

export function buildPriorityDonutData(
  issues: IssueItem[],
  stateFilter: "opened" | "closed",
  palette: Record<string, string>,
  priorityOrder: string[],
  theme: ThemeMode,
): DonutModel {
  const colorMap = buildPriorityColorMap(issues, palette, priorityOrder, theme);
  const matching = issues.filter((issue) => issue.state === stateFilter);
  const counts = new Map<string, { count: number; rank: number | null }>();

  for (const issue of matching) {
    const label = issue.priority || "Unset";
    const prev = counts.get(label);
    if (!prev) {
      counts.set(label, { count: 1, rank: issue.priority_rank });
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

  const slices = Array.from(counts.entries())
    .sort((a, b) => {
      const aUnset = a[0] === "Unset" ? 1 : 0;
      const bUnset = b[0] === "Unset" ? 1 : 0;
      if (aUnset !== bUnset) return aUnset - bUnset;
      const rankA = a[1].rank ?? Number.MAX_SAFE_INTEGER;
      const rankB = b[1].rank ?? Number.MAX_SAFE_INTEGER;
      if (rankA !== rankB) return rankA - rankB;
      return a[0].localeCompare(b[0]);
    })
    .map(([label, stat]) => ({
      label,
      count: stat.count,
      color: colorMap[label] ?? colorMap.Unset,
    }));

  return { total: matching.length, slices };
}

const CANONICAL_ISSUE_TYPE_ORDER = ["bug", "feature", "task", "epic"];

export function buildIssueTypeDonutData(
  issues: IssueItem[],
  stateFilter: "opened" | "closed",
  palette: Record<string, string>,
  theme: ThemeMode,
): DonutModel {
  const matching = issues.filter((issue) => issue.state === stateFilter);
  const counts = new Map<string, number>();

  for (const issue of matching) {
    const label = (issue.issue_type || "Unset").trim() || "Unset";
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }

  const slices = Array.from(counts.entries())
    .sort((a, b) => {
      const aNorm = a[0].toLowerCase();
      const bNorm = b[0].toLowerCase();
      const aUnset = aNorm === "unset" ? 1 : 0;
      const bUnset = bNorm === "unset" ? 1 : 0;
      if (aUnset !== bUnset) return aUnset - bUnset;
      const idxA = CANONICAL_ISSUE_TYPE_ORDER.indexOf(aNorm);
      const idxB = CANONICAL_ISSUE_TYPE_ORDER.indexOf(bNorm);
      if (idxA >= 0 && idxB >= 0 && idxA !== idxB) return idxA - idxB;
      if (idxA >= 0 && idxB < 0) return -1;
      if (idxB >= 0 && idxA < 0) return 1;
      return a[0].localeCompare(b[0]);
    })
    .map(([label, count], idx) => ({
      label,
      count,
      color: getIssueTypeColor(label, palette, theme, idx),
    }));

  return { total: matching.length, slices };
}

export interface QualitySignalBar {
  code: string;
  label: string;
  count: number;
  color: string;
}

function formatCodeLabel(code: string): string {
  return code
    .toLowerCase()
    .split("_")
    .map((part) => (part ? part[0].toUpperCase() + part.slice(1) : ""))
    .join(" ");
}

export function buildQualitySignalsData(
  issues: IssueItem[],
  palette: Record<string, string>,
): QualitySignalBar[] {
  const counts = new Map<string, number>();
  for (const issue of issues) {
    if (issue.state !== "opened") continue;
    for (const signal of issue.quality_signals) {
      counts.set(signal, (counts.get(signal) ?? 0) + 1);
    }
  }

  const cycleColors = [
    palette.task ?? "#4facfe",
    palette.waiting ?? "#f4a44a",
    palette.epic ?? "#c76bff",
    palette.bug ?? "#f5576c",
    palette.high ?? "#e88236",
    palette.feature ?? "#56d4b0",
    palette.neutral ?? "#7a8fa8",
  ];

  return Array.from(counts.entries())
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .map(([code, count], idx) => ({
      code,
      label: formatCodeLabel(code),
      count,
      color: cycleColors[idx % cycleColors.length],
    }));
}

export interface VelocityDay {
  isoDate: string;
  label: string;
  created: number;
  closed: number;
}

function parseUtcDayMs(rawTimestamp: string | null | undefined): number | null {
  if (!rawTimestamp || rawTimestamp.length < 10) return null;
  const isoDay = rawTimestamp.slice(0, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(isoDay)) return null;
  const ms = Date.parse(`${isoDay}T00:00:00Z`);
  return Number.isNaN(ms) ? null : ms;
}

export function buildDailyVelocityData(
  issues: IssueItem[],
  now: Date = new Date(),
): VelocityDay[] {
  const todayUtc = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  let latestEventDayUtc: number | null = null;

  for (const issue of issues) {
    const createdDayMs = parseUtcDayMs(issue.created_at);
    if (createdDayMs !== null && (latestEventDayUtc === null || createdDayMs > latestEventDayUtc)) {
      latestEventDayUtc = createdDayMs;
    }
    const closedDayMs = parseUtcDayMs(issue.closed_at);
    if (closedDayMs !== null && (latestEventDayUtc === null || closedDayMs > latestEventDayUtc)) {
      latestEventDayUtc = closedDayMs;
    }
  }

  const windowStartDefault = todayUtc - 6 * 86_400_000;
  const anchorUtc =
    latestEventDayUtc !== null && latestEventDayUtc < windowStartDefault
      ? latestEventDayUtc
      : todayUtc;

  const days: VelocityDay[] = [];
  const byDate = new Map<string, VelocityDay>();

  for (let offset = 6; offset >= 0; offset -= 1) {
    const dt = new Date(anchorUtc - offset * 86_400_000);
    const isoDate = dt.toISOString().slice(0, 10);
    const label = dt.toLocaleDateString("en-US", {
      month: "short",
      day: "2-digit",
      timeZone: "UTC",
    });
    const item: VelocityDay = { isoDate, label, created: 0, closed: 0 };
    days.push(item);
    byDate.set(isoDate, item);
  }

  for (const issue of issues) {
    const createdDay = issue.created_at.slice(0, 10);
    const createdHit = byDate.get(createdDay);
    if (createdHit) {
      createdHit.created += 1;
    }
    if (issue.closed_at) {
      const closedDay = issue.closed_at.slice(0, 10);
      const closedHit = byDate.get(closedDay);
      if (closedHit) {
        closedHit.closed += 1;
      }
    }
  }
  return days;
}

/**
 * Indices of evenly spaced x-axis points whose labels can be drawn without
 * overlapping, counted back from the last point so the most recent day keeps
 * its label.
 */
export function pickAxisLabelIndices(count: number, spacing: number, labelWidth: number): number[] {
  const step = Math.max(1, Math.ceil(labelWidth / Math.max(spacing, 1)));
  const indices: number[] = [];
  for (let idx = count - 1; idx >= 0; idx -= step) {
    indices.unshift(idx);
  }
  return indices;
}

export interface StageBarBucket {
  stage: string;
  total: number;
  filterState: "opened" | "closed" | "all";
  isClosedOnly: boolean;
  bars: Array<{ priority: string; count: number; color: string }>;
}

export function buildStagePriorityBars(
  issues: IssueItem[],
  stages: string[],
  palette: Record<string, string>,
  priorityOrder: string[],
  theme: ThemeMode,
): StageBarBucket[] {
  const colorMap = buildPriorityColorMap(issues, palette, priorityOrder, theme);

  const buckets = stages
    .map((stage): StageBarBucket | null => {
      const counts = new Map<string, { count: number; rank: number | null }>();
      let hasOpened = false;
      let hasClosed = false;
      let total = 0;

      for (const issue of issues) {
        if (issue.stage !== stage) continue;
        total += 1;
        if (issue.state === "opened") {
          hasOpened = true;
        } else if (issue.state === "closed") {
          hasClosed = true;
        }
        const prio = issue.priority || "Unset";
        const prev = counts.get(prio);
        if (!prev) {
          counts.set(prio, { count: 1, rank: issue.priority_rank });
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

      if (total === 0) return null;

      const filterState: "opened" | "closed" | "all" =
        hasOpened && hasClosed ? "all" : hasClosed ? "closed" : "opened";
      const isClosedOnly = hasClosed && !hasOpened;

      const bars = Array.from(counts.entries())
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

      return { stage, total, filterState, isClosedOnly, bars };
    })
    .filter((bucket): bucket is StageBarBucket => bucket !== null);

  const openOrMixed = buckets.filter((b) => !b.isClosedOnly);
  const closedOnly = buckets.filter((b) => b.isClosedOnly);
  return [...openOrMixed, ...closedOnly];
}

/**
 * Formats a count as a whole-percent share of a total.
 *
 * @param count Part of the total.
 * @param total Total the share is measured against.
 * @returns "0%" for an empty total, "<1%" for tiny nonzero shares, else a rounded percent.
 */
export function formatShare(count: number, total: number): string {
  if (total <= 0) return "0%";
  const pct = (count / total) * 100;
  if (pct > 0 && pct < 0.5) return "<1%";
  return `${Math.round(pct)}%`;
}
