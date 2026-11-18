import type { IssueItem, ThemeMode } from "./types";

const PRIORITY_RING_DARK = ["#dd2476", "#f4a44a", "#56d4b0", "#4facfe", "#c76bff"];
const PRIORITY_RING_LIGHT = ["#b51c3c", "#b06000", "#1a7a62", "#005e9e", "#8a0ea8"];
const TYPE_RING_DARK = ["#4facfe", "#c76bff", "#f4a44a", "#56d4b0", "#f5576c"];
const TYPE_RING_LIGHT = ["#005e9e", "#8a0ea8", "#b06000", "#1a7a62", "#b51c3c"];

export function getIssueTypeColor(
  issueType: string,
  palette: Record<string, string>,
  theme: ThemeMode,
  fallbackIndex = 0,
): string {
  const normalized = issueType.trim().toLowerCase();
  if (!normalized || normalized === "unset") {
    return palette.unset ?? palette.neutral ?? (theme === "dark" ? "#7a8fa8" : "#3d5370");
  }
  const direct = palette[normalized];
  if (direct) {
    return direct;
  }
  const ring = theme === "dark" ? TYPE_RING_DARK : TYPE_RING_LIGHT;
  return ring[Math.abs(fallbackIndex) % ring.length];
}

export function getPriorityColor(
  priority: string,
  palette: Record<string, string>,
  priorityOrder: string[],
  theme: ThemeMode,
): string {
  const normalized = priority.trim().toLowerCase();
  if (!normalized || normalized === "unset") {
    return palette.unset ?? palette.neutral ?? (theme === "dark" ? "#7a8fa8" : "#3d5370");
  }
  const direct = palette[normalized];
  if (direct) {
    return direct;
  }
  const rankIdx = priorityOrder.findIndex((item) => item.toLowerCase() === normalized);
  const ring = theme === "dark" ? PRIORITY_RING_DARK : PRIORITY_RING_LIGHT;
  if (rankIdx >= 0) {
    return ring[Math.min(rankIdx, ring.length - 1)];
  }
  return palette.neutral ?? (theme === "dark" ? "#7a8fa8" : "#3d5370");
}

export function buildPriorityColorMap(
  issues: IssueItem[],
  palette: Record<string, string>,
  priorityOrder: string[],
  theme: ThemeMode,
): Record<string, string> {
  const rankByLabel = new Map<string, number>();
  priorityOrder.forEach((label, idx) => rankByLabel.set(label, idx));

  for (const issue of issues) {
    const label = issue.priority || "Unset";
    if (label === "Unset") {
      continue;
    }
    if (issue.priority_rank !== null) {
      const existing = rankByLabel.get(label);
      if (existing === undefined || issue.priority_rank < existing) {
        rankByLabel.set(label, issue.priority_rank);
      }
    } else if (!rankByLabel.has(label)) {
      rankByLabel.set(label, Number.MAX_SAFE_INTEGER);
    }
  }

  const ordered = Array.from(rankByLabel.entries()).sort((a, b) => {
    if (a[1] !== b[1]) return a[1] - b[1];
    return a[0].localeCompare(b[0]);
  });

  const ring = theme === "dark" ? PRIORITY_RING_DARK : PRIORITY_RING_LIGHT;
  const map: Record<string, string> = {};
  ordered.forEach(([label], idx) => {
    const paletteHit = palette[label.toLowerCase()];
    map[label] = paletteHit ?? ring[Math.min(idx, ring.length - 1)];
  });
  map.Unset = palette.unset ?? palette.neutral ?? (theme === "dark" ? "#7a8fa8" : "#3d5370");
  return map;
}

export function hexWithAlpha(hexOrColor: string, alpha: number): string {
  const trimmed = hexOrColor.trim();
  if (trimmed.startsWith("#")) {
    let hex = trimmed.slice(1);
    if (hex.length === 3) {
      hex = hex
        .split("")
        .map((c) => c + c)
        .join("");
    }
    if (hex.length === 6) {
      const r = Number.parseInt(hex.slice(0, 2), 16);
      const g = Number.parseInt(hex.slice(2, 4), 16);
      const b = Number.parseInt(hex.slice(4, 6), 16);
      if (!Number.isNaN(r) && !Number.isNaN(g) && !Number.isNaN(b)) {
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
      }
    }
  }
  return trimmed;
}

function linearizeChannel(channel255: number): number {
  const c = channel255 / 255;
  return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
}

export function contrastTextForHex(hexOrColor: string): string {
  const trimmed = hexOrColor.trim();
  if (!trimmed.startsWith("#")) {
    return "#ffffff";
  }
  let hex = trimmed.slice(1);
  if (hex.length === 3) {
    hex = hex
      .split("")
      .map((c) => c + c)
      .join("");
  }
  if (hex.length !== 6) {
    return "#ffffff";
  }
  const r = Number.parseInt(hex.slice(0, 2), 16);
  const g = Number.parseInt(hex.slice(2, 4), 16);
  const b = Number.parseInt(hex.slice(4, 6), 16);
  if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b)) {
    return "#ffffff";
  }
  const luminance =
    0.2126 * linearizeChannel(r) +
    0.7152 * linearizeChannel(g) +
    0.0722 * linearizeChannel(b);
  return luminance > 0.36 ? "#0b0d17" : "#ffffff";
}
