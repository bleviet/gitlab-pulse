import { normalizeSearchText, similarityRatio } from "./search";
import type { GlobalFilters, IssueItem } from "./types";

export type ScopeDimension = "team" | "context" | "milestone";

export interface ScopeOptionMatch {
  kind: "single";
  id: string;
  dimension: ScopeDimension;
  value: string;
  count: number;
  score: number;
}

export interface ScopeCombinedMatch {
  kind: "combined";
  id: string;
  patch: Partial<Pick<GlobalFilters, "team" | "context" | "milestone">>;
  labels: Array<{ dimension: ScopeDimension; value: string }>;
  count: number;
  score: number;
}

export interface ScopeSearchResult {
  combined: ScopeCombinedMatch[];
  teams: ScopeOptionMatch[];
  contexts: ScopeOptionMatch[];
  milestones: ScopeOptionMatch[];
}

function compactAlnum(normalizedText: string): string {
  return normalizedText.replace(/[^a-z0-9]/g, "");
}

function isOrderedSubsequence(needle: string, haystack: string): boolean {
  if (!needle) return false;
  let ni = 0;
  for (let hi = 0; hi < haystack.length && ni < needle.length; hi += 1) {
    if (haystack[hi] === needle[ni]) {
      ni += 1;
    }
  }
  return ni === needle.length;
}

function scoreSingleWord(
  candNorm: string,
  candCompact: string,
  candWords: string[],
  qNorm: string,
  qCompact: string,
): number {
  if (candNorm === qNorm || candCompact === qCompact) return 100;
  if (candNorm.startsWith(qNorm) || candCompact.startsWith(qCompact)) return 90;
  if (candNorm.includes(qNorm) || candCompact.includes(qCompact)) return 76;

  if (qCompact.length >= 3) {
    if (isOrderedSubsequence(qCompact, candCompact)) {
      return 62;
    }
    let best = similarityRatio(qCompact, candCompact);
    for (const cw of candWords) {
      const cwCompact = compactAlnum(cw);
      if (!cwCompact) continue;
      const ratio = similarityRatio(qCompact, cwCompact);
      if (ratio > best) best = ratio;
    }
    const threshold = qCompact.length <= 4 ? 0.78 : 0.72;
    if (best >= threshold) {
      return Math.round(best * 68);
    }
  }

  return 0;
}

export function scoreScopeCandidate(candidate: string, queryPart: string): number {
  const qNorm = normalizeSearchText(queryPart);
  const qCompact = compactAlnum(qNorm);
  if (!qNorm || !qCompact) return 0;

  const candNorm = normalizeSearchText(candidate);
  const candCompact = compactAlnum(candNorm);
  if (!candNorm || !candCompact) return 0;

  if (candNorm === qNorm || candCompact === qCompact) return 100;
  if (candNorm.startsWith(qNorm) || candCompact.startsWith(qCompact)) return 90;

  const qWords = qNorm.split(" ").filter(Boolean);
  const candWords = candNorm.split(" ").filter(Boolean);

  if (qWords.length <= 1) {
    return scoreSingleWord(candNorm, candCompact, candWords, qNorm, qCompact);
  }

  if (candWords.length >= qWords.length) {
    let ci = 0;
    const allWordPrefix = qWords.every((qw) => {
      while (ci < candWords.length) {
        if (candWords[ci].startsWith(qw)) {
          ci += 1;
          return true;
        }
        ci += 1;
      }
      return false;
    });
    if (allWordPrefix) return 84;
  }

  if (candNorm.includes(qNorm) || candCompact.includes(qCompact)) return 76;

  let scoreSum = 0;
  for (const qw of qWords) {
    const qwCompact = compactAlnum(qw);
    if (!qwCompact) continue;
    const wordScore = scoreSingleWord(candNorm, candCompact, candWords, qw, qwCompact);
    if (wordScore === 0) return 0;
    scoreSum += wordScore;
  }
  return Math.round((scoreSum / qWords.length) * 0.8);
}

function filterByDateRange(
  issues: IssueItem[],
  startDate: string,
  endDate: string,
): IssueItem[] {
  const startMs = startDate ? Date.parse(`${startDate}T00:00:00.000Z`) : null;
  const endMs = endDate ? Date.parse(`${endDate}T23:59:59.999Z`) : null;
  if (startMs === null && endMs === null) return issues;

  return issues.filter((issue) => {
    const createdMs = Date.parse(issue.created_at);
    if (Number.isNaN(createdMs)) return false;
    if (startMs !== null && !Number.isNaN(startMs) && createdMs < startMs) return false;
    if (endMs !== null && !Number.isNaN(endMs) && createdMs > endMs) return false;
    return true;
  });
}

const THREE_WAY_ORDERINGS: Array<[ScopeDimension, ScopeDimension, ScopeDimension]> = [
  ["team", "context", "milestone"],
  ["team", "milestone", "context"],
  ["context", "team", "milestone"],
  ["context", "milestone", "team"],
  ["milestone", "team", "context"],
  ["milestone", "context", "team"],
];

export function buildScopeSuggestions(
  issues: IssueItem[],
  filters: GlobalFilters,
  options: { teams: string[]; contexts: string[]; milestones: string[] },
  rawQuery: string,
): ScopeSearchResult {
  const dateScopedIssues = filterByDateRange(issues, filters.startDate, filters.endDate);
  const showTeams = options.teams.length > 1;

  const countWithPatch = (
    patch: Partial<Pick<GlobalFilters, "team" | "context" | "milestone">>,
  ): number => {
    const targetTeam = patch.team ?? filters.team;
    const targetContext = patch.context ?? filters.context;
    const targetMilestone = patch.milestone ?? filters.milestone;
    let total = 0;
    for (const issue of dateScopedIssues) {
      if (targetTeam !== "All" && issue.team !== targetTeam) continue;
      if (targetContext !== "All" && !issue.contexts.includes(targetContext)) continue;
      if (targetMilestone !== "All" && issue.milestone !== targetMilestone) continue;
      total += 1;
    }
    return total;
  };

  const trimmedQuery = rawQuery.trim();
  const normalizedQuery = normalizeSearchText(trimmedQuery);
  const words = normalizedQuery ? normalizedQuery.split(" ").filter(Boolean) : [];

  const scoreSingle = (
    dimension: ScopeDimension,
    values: string[],
    activeValue: string,
  ): ScopeOptionMatch[] => {
    const matches: ScopeOptionMatch[] = [];
    for (const value of values) {
      if (value === activeValue) continue;
      const count = countWithPatch({ [dimension]: value });
      if (count === 0) continue;

      let score = 1;
      if (trimmedQuery) {
        score = scoreScopeCandidate(value, trimmedQuery);
        if (score === 0 && words.length >= 2) {
          for (const word of words) {
            const wordScore = scoreScopeCandidate(value, word);
            if (wordScore > score) score = wordScore;
          }
        }
        if (score === 0) continue;
      }

      matches.push({
        kind: "single",
        id: `${dimension}:${value}`,
        dimension,
        value,
        count,
        score,
      });
    }

    if (trimmedQuery) {
      matches.sort(
        (a, b) => b.score - a.score || b.count - a.count || a.value.localeCompare(b.value),
      );
    }
    return matches;
  };

  const teams = showTeams ? scoreSingle("team", options.teams, filters.team) : [];
  const contexts = scoreSingle("context", options.contexts, filters.context);
  const milestones = scoreSingle("milestone", options.milestones, filters.milestone);

  if (words.length < 2) {
    return { combined: [], teams, contexts, milestones };
  }

  const combinedByKey = new Map<string, ScopeCombinedMatch>();

  const valuesForDim = (dim: ScopeDimension): string[] => {
    if (dim === "team") return showTeams ? options.teams : [];
    return dim === "context" ? options.contexts : options.milestones;
  };

  const activeForDim = (dim: ScopeDimension): string => {
    if (dim === "team") return filters.team;
    return dim === "context" ? filters.context : filters.milestone;
  };

  const tryRegisterCombined = (
    entries: Array<{ dimension: ScopeDimension; queryPart: string }>,
  ): void => {
    const perDimMatches = entries.map(({ dimension, queryPart }) => {
      const activeVal = activeForDim(dimension);
      const scored: Array<{ value: string; score: number }> = [];
      for (const value of valuesForDim(dimension)) {
        if (value === activeVal) continue;
        const score = scoreScopeCandidate(value, queryPart);
        if (score > 0) {
          scored.push({ value, score });
        }
      }
      scored.sort((a, b) => b.score - a.score || a.value.localeCompare(b.value));
      return { dimension, candidates: scored.slice(0, 6) };
    });

    if (perDimMatches.some((item) => item.candidates.length === 0)) return;

    const visit = (
      idx: number,
      patch: Partial<Pick<GlobalFilters, "team" | "context" | "milestone">>,
      labels: Array<{ dimension: ScopeDimension; value: string }>,
      scoreSum: number,
    ): void => {
      if (idx === perDimMatches.length) {
        const count = countWithPatch(patch);
        if (count === 0) return;
        const avgScore = Math.round(scoreSum / perDimMatches.length);
        const key = `${patch.team ?? ""}|${patch.context ?? ""}|${patch.milestone ?? ""}`;
        const existing = combinedByKey.get(key);
        if (!existing || avgScore > existing.score) {
          combinedByKey.set(key, {
            kind: "combined",
            id: `combined:${key}`,
            patch,
            labels,
            count,
            score: avgScore,
          });
        }
        return;
      }

      const { dimension, candidates } = perDimMatches[idx];
      for (const cand of candidates) {
        visit(
          idx + 1,
          { ...patch, [dimension]: cand.value },
          [...labels, { dimension, value: cand.value }],
          scoreSum + cand.score,
        );
      }
    };

    visit(0, {}, [], 0);
  };

  const pairDims: Array<[ScopeDimension, ScopeDimension]> = showTeams
    ? [
        ["context", "milestone"],
        ["team", "context"],
        ["team", "milestone"],
      ]
    : [["context", "milestone"]];

  for (let k = 1; k < words.length; k += 1) {
    const left = words.slice(0, k).join(" ");
    const right = words.slice(k).join(" ");
    for (const [dimA, dimB] of pairDims) {
      tryRegisterCombined([
        { dimension: dimA, queryPart: left },
        { dimension: dimB, queryPart: right },
      ]);
      tryRegisterCombined([
        { dimension: dimA, queryPart: right },
        { dimension: dimB, queryPart: left },
      ]);
    }
  }

  if (showTeams && words.length >= 3) {
    for (let i = 1; i < words.length - 1; i += 1) {
      for (let j = i + 1; j < words.length; j += 1) {
        const p1 = words.slice(0, i).join(" ");
        const p2 = words.slice(i, j).join(" ");
        const p3 = words.slice(j).join(" ");
        for (const [d1, d2, d3] of THREE_WAY_ORDERINGS) {
          tryRegisterCombined([
            { dimension: d1, queryPart: p1 },
            { dimension: d2, queryPart: p2 },
            { dimension: d3, queryPart: p3 },
          ]);
        }
      }
    }
  }

  const combined = Array.from(combinedByKey.values())
    .sort((a, b) => b.score - a.score || b.count - a.count || a.id.localeCompare(b.id))
    .slice(0, 4);

  return { combined, teams, contexts, milestones };
}
