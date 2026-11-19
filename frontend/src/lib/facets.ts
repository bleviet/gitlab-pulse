import { filterIssuesBySearch } from "./search";
import type {
  FilterOptions,
  GlobalFilters,
  IssueFacets,
  IssueItem,
  TimePreset,
} from "./types";

export const RECENT_DAYS = 7;
export const FACET_QUERY_PREFIX = "f_";
const SUMMARY_QUERY_KEY = "summary";
const VIEW_QUERY_KEY = "view";

const FACET_KEYS: Array<keyof IssueFacets> = [
  "stage",
  "state",
  "priority",
  "issue_type",
  "signal",
  "query",
  "recent",
  "day",
  "day_kind",
];

export interface FilterChip {
  kind: "facet" | "sidebar";
  key: string;
  label: string;
}

export function cleanFacets(raw: Partial<Record<keyof IssueFacets, unknown>>): IssueFacets {
  const cleaned: IssueFacets = {};
  const strVal = (key: keyof IssueFacets): string | undefined => {
    const val = raw[key];
    if (val === null || val === undefined) return undefined;
    const trimmed = String(val).trim();
    return trimmed ? trimmed : undefined;
  };

  const stage = strVal("stage");
  if (stage) cleaned.stage = stage;

  const state = strVal("state");
  if (state === "opened" || state === "closed" || state === "all") {
    cleaned.state = state;
  }

  const priority = strVal("priority");
  if (priority) cleaned.priority = priority;

  const issueType = strVal("issue_type");
  if (issueType) cleaned.issue_type = issueType;

  const signal = strVal("signal");
  if (signal) cleaned.signal = signal;

  const query = strVal("query");
  if (query) cleaned.query = query;

  const recent = strVal("recent");
  if (recent === "created" || recent === "closed") {
    cleaned.recent = recent;
  }

  const day = strVal("day");
  const dayKind = strVal("day_kind");
  if (
    day &&
    /^\d{4}-\d{2}-\d{2}$/.test(day) &&
    !Number.isNaN(Date.parse(`${day}T00:00:00Z`)) &&
    (dayKind === "created" || dayKind === "closed")
  ) {
    cleaned.day = day;
    cleaned.day_kind = dayKind;
  }

  return cleaned;
}

export function withoutFacet(facets: IssueFacets, key: keyof IssueFacets): IssueFacets {
  const next: Partial<Record<keyof IssueFacets, unknown>> = { ...facets };
  delete next[key];
  if (key === "day") {
    delete next.day_kind;
  }
  return cleanFacets(next);
}

export function applyPreMilestoneFilters(
  issues: IssueItem[],
  filters: Pick<GlobalFilters, "team" | "context">,
): IssueItem[] {
  return issues.filter((issue) => {
    if (filters.team !== "All" && issue.team !== filters.team) {
      return false;
    }
    if (filters.context !== "All" && !issue.contexts.includes(filters.context)) {
      return false;
    }
    return true;
  });
}

export function applyGlobalFilters(issues: IssueItem[], filters: GlobalFilters): IssueItem[] {
  const startMs = filters.startDate ? Date.parse(`${filters.startDate}T00:00:00.000Z`) : null;
  const endMs = filters.endDate ? Date.parse(`${filters.endDate}T23:59:59.999Z`) : null;

  return issues.filter((issue) => {
    if (filters.team !== "All" && issue.team !== filters.team) {
      return false;
    }
    if (filters.context !== "All" && !issue.contexts.includes(filters.context)) {
      return false;
    }
    if (filters.milestone !== "All" && issue.milestone !== filters.milestone) {
      return false;
    }
    if (startMs !== null || endMs !== null) {
      const createdMs = Date.parse(issue.created_at);
      if (Number.isNaN(createdMs)) return false;
      if (startMs !== null && !Number.isNaN(startMs) && createdMs < startMs) return false;
      if (endMs !== null && !Number.isNaN(endMs) && createdMs > endMs) return false;
    }
    return true;
  });
}

export function isRecentIssue(
  issue: IssueItem,
  kind: "created" | "closed",
  now: Date = new Date(),
): boolean {
  const rawDate = kind === "closed" ? issue.closed_at : issue.created_at;
  if (!rawDate) return false;
  if (kind === "closed" && issue.state !== "closed") return false;

  const ts = Date.parse(rawDate);
  if (Number.isNaN(ts)) return false;

  const todayStartUtc = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  const windowStartUtc = todayStartUtc - (RECENT_DAYS - 1) * 86_400_000;
  return ts >= windowStartUtc;
}

export function applyFacets(
  issues: IssueItem[],
  facets: IssueFacets,
  now: Date = new Date(),
): IssueItem[] {
  const effectiveState = facets.state ?? "opened";

  let result = issues.filter((issue) => {
    if (facets.stage && issue.stage !== facets.stage) {
      return false;
    }
    if ((effectiveState === "opened" || effectiveState === "closed") && issue.state !== effectiveState) {
      return false;
    }
    if (facets.recent && !isRecentIssue(issue, facets.recent, now)) {
      return false;
    }
    if (facets.day) {
      const dateStr = facets.day_kind === "closed" ? issue.closed_at : issue.created_at;
      if (!dateStr || dateStr.slice(0, 10) !== facets.day) {
        return false;
      }
    }
    if (facets.signal) {
      const targetSignal = facets.signal.trim().toUpperCase();
      if (!issue.quality_signals.includes(targetSignal)) {
        return false;
      }
    }
    if (facets.priority) {
      const targetPrio = facets.priority.trim().toLowerCase();
      const issuePrio = (issue.priority || "Unset").trim().toLowerCase();
      if (issuePrio !== targetPrio) {
        return false;
      }
    }
    if (facets.issue_type) {
      const targetType = facets.issue_type.trim().toLowerCase();
      const issueType = (issue.issue_type || "Unset").trim().toLowerCase();
      if (issueType !== targetType) {
        return false;
      }
    }
    return true;
  });

  if (facets.query) {
    result = filterIssuesBySearch(result, facets.query);
  }
  return result;
}

function formatDayLabel(isoDate: string): string {
  const parsed = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return isoDate;
  return parsed.toLocaleDateString("en-US", {
    month: "short",
    day: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  });
}

function formatSignalLabel(code: string): string {
  return code
    .toLowerCase()
    .split("_")
    .map((part) => (part ? part[0].toUpperCase() + part.slice(1) : ""))
    .join(" ");
}

export function buildFacetChips(
  facets: IssueFacets,
  globalFilters: GlobalFilters,
  defaultStartDate: string,
  defaultEndDate: string,
): FilterChip[] {
  const chips: FilterChip[] = [];

  if (facets.stage) {
    chips.push({ kind: "facet", key: "stage", label: `Stage: ${facets.stage}` });
  }
  if ((facets.state === "closed" || facets.state === "all") && !facets.recent && !facets.day) {
    const label = facets.state === "closed" ? "Closed" : "All";
    chips.push({ kind: "facet", key: "state", label: `State: ${label}` });
  }
  if (facets.priority) {
    chips.push({ kind: "facet", key: "priority", label: `Priority: ${facets.priority}` });
  }
  if (facets.issue_type) {
    chips.push({ kind: "facet", key: "issue_type", label: `Type: ${facets.issue_type}` });
  }
  if (facets.signal) {
    chips.push({ kind: "facet", key: "signal", label: `Signal: ${formatSignalLabel(facets.signal)}` });
  }
  if (facets.recent) {
    const prefix = facets.recent === "closed" ? "Closed" : "Created";
    chips.push({ kind: "facet", key: "recent", label: `${prefix}: last ${RECENT_DAYS} days` });
  }
  if (facets.day) {
    const prefix = facets.day_kind === "closed" ? "Closed" : "Created";
    chips.push({ kind: "facet", key: "day", label: `${prefix}: ${formatDayLabel(facets.day)}` });
  }
  if (facets.query) {
    chips.push({ kind: "facet", key: "query", label: `Search: ${facets.query}` });
  }

  if (globalFilters.team !== "All") {
    chips.push({ kind: "sidebar", key: "team", label: `Domain / Team: ${globalFilters.team}` });
  }
  if (globalFilters.context !== "All") {
    chips.push({ kind: "sidebar", key: "context", label: `Context: ${globalFilters.context}` });
  }
  if (globalFilters.milestone !== "All") {
    chips.push({ kind: "sidebar", key: "milestone", label: `Milestone: ${globalFilters.milestone}` });
  }
  const hasCustomDates =
    Boolean(globalFilters.startDate && globalFilters.endDate) &&
    (globalFilters.startDate !== defaultStartDate || globalFilters.endDate !== defaultEndDate);
  if (hasCustomDates) {
    const label =
      globalFilters.preset === "30d"
        ? "30 Days"
        : globalFilters.preset === "90d"
          ? "90 Days"
          : globalFilters.preset === "1y"
            ? "1 Year"
            : `${globalFilters.startDate} to ${globalFilters.endDate}`;
    chips.push({ kind: "sidebar", key: "date_range", label: `Time: ${label}` });
  }

  return chips;
}

const PRESET_VALUES: TimePreset[] = ["30d", "90d", "1y", "all", "custom"];

function isValidIsoDate(value: string | null): value is string {
  return Boolean(
    value &&
      /^\d{4}-\d{2}-\d{2}$/.test(value) &&
      !Number.isNaN(Date.parse(`${value}T00:00:00Z`)),
  );
}

export function subtractDaysIso(endIso: string, days: number, minIso: string): string {
  const endMs = Date.parse(`${endIso}T00:00:00Z`);
  if (Number.isNaN(endMs)) return minIso;
  const candidate = new Date(endMs - days * 86_400_000).toISOString().slice(0, 10);
  return minIso && candidate < minIso ? minIso : candidate;
}

export function resolvePresetDates(
  preset: TimePreset,
  minDate: string,
  maxDate: string,
  currentStart = "",
  currentEnd = "",
): { startDate: string; endDate: string } {
  if (preset === "all") {
    return { startDate: minDate, endDate: maxDate };
  }
  if (preset === "custom") {
    return {
      startDate: currentStart || minDate,
      endDate: currentEnd || maxDate,
    };
  }
  const days = preset === "30d" ? 30 : preset === "90d" ? 90 : 365;
  return {
    startDate: maxDate ? subtractDaysIso(maxDate, days, minDate) : minDate,
    endDate: maxDate,
  };
}

export function deriveScopedFilterOptions(
  issues: IssueItem[],
  filters: Pick<GlobalFilters, "team" | "context">,
  baseOptions: FilterOptions,
): { teams: string[]; contexts: string[]; milestones: string[] } {
  const contexts = (() => {
    if (filters.team === "All") return baseOptions.contexts;
    const contextSet = new Set<string>();
    for (const issue of issues) {
      if (issue.team !== filters.team) continue;
      for (const ctx of issue.contexts) {
        contextSet.add(ctx);
      }
    }
    return baseOptions.contexts.filter((c) => contextSet.has(c));
  })();

  const milestones = (() => {
    if (filters.team === "All" && filters.context === "All") {
      return baseOptions.milestones;
    }
    const milestoneSet = new Set<string>();
    for (const issue of issues) {
      if (filters.team !== "All" && issue.team !== filters.team) continue;
      if (filters.context !== "All" && !issue.contexts.includes(filters.context)) continue;
      if (issue.milestone) {
        milestoneSet.add(issue.milestone);
      }
    }
    return baseOptions.milestones.filter((m) => milestoneSet.has(m));
  })();

  return {
    teams: baseOptions.teams,
    contexts,
    milestones,
  };
}

export function parseGlobalFiltersUrl(search: string): Partial<GlobalFilters> {
  const params = new URLSearchParams(search);
  const parsed: Partial<GlobalFilters> = {};

  const team = (params.get("g_team") ?? "").trim();
  if (team && team !== "All") parsed.team = team;

  const context = (params.get("g_context") ?? "").trim();
  if (context && context !== "All") parsed.context = context;

  const milestone = (params.get("g_milestone") ?? "").trim();
  if (milestone && milestone !== "All") parsed.milestone = milestone;

  const presetRaw = (params.get("g_preset") ?? "").trim().toLowerCase();
  if (PRESET_VALUES.includes(presetRaw as TimePreset)) {
    const preset = presetRaw as TimePreset;
    parsed.preset = preset;
    if (preset === "custom") {
      const start = (params.get("g_start") ?? "").trim();
      const end = (params.get("g_end") ?? "").trim();
      if (isValidIsoDate(start)) parsed.startDate = start;
      if (isValidIsoDate(end)) parsed.endDate = end;
    }
  }

  return parsed;
}

export function parseUrlState(search: string): {
  chartsVisible: boolean;
  summaryId: string | null;
  facets: IssueFacets;
} {
  const params = new URLSearchParams(search);
  const viewRaw = (params.get(VIEW_QUERY_KEY) ?? "").trim().toLowerCase();
  const chartsVisible = viewRaw !== "compact";
  const summaryRaw = (params.get(SUMMARY_QUERY_KEY) ?? "").trim();
  const summaryId = summaryRaw || null;

  const rawFacets: Partial<Record<keyof IssueFacets, string>> = {};
  for (const key of FACET_KEYS) {
    const val = params.get(`${FACET_QUERY_PREFIX}${key}`);
    if (val !== null) {
      rawFacets[key] = val;
    }
  }
  return { chartsVisible, summaryId, facets: cleanFacets(rawFacets) };
}

export function buildUrlSearch(
  chartsVisible: boolean,
  summaryId: string | null,
  facets: IssueFacets,
  globalFilters?: Partial<GlobalFilters>,
): string {
  const params = new URLSearchParams();
  if (!chartsVisible) {
    params.set(VIEW_QUERY_KEY, "compact");
  }
  if (summaryId) {
    params.set(SUMMARY_QUERY_KEY, summaryId);
  }
  for (const key of FACET_KEYS) {
    const val = facets[key];
    if (val) {
      params.set(`${FACET_QUERY_PREFIX}${key}`, val);
    }
  }
  if (globalFilters) {
    if (globalFilters.team && globalFilters.team !== "All") {
      params.set("g_team", globalFilters.team);
    }
    if (globalFilters.context && globalFilters.context !== "All") {
      params.set("g_context", globalFilters.context);
    }
    if (globalFilters.milestone && globalFilters.milestone !== "All") {
      params.set("g_milestone", globalFilters.milestone);
    }
    if (globalFilters.preset && globalFilters.preset !== "all") {
      params.set("g_preset", globalFilters.preset);
      if (globalFilters.preset === "custom") {
        if (isValidIsoDate(globalFilters.startDate ?? null)) {
          params.set("g_start", globalFilters.startDate as string);
        }
        if (isValidIsoDate(globalFilters.endDate ?? null)) {
          params.set("g_end", globalFilters.endDate as string);
        }
      }
    }
  }
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}
