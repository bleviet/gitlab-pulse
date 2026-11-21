import type {
  ClassificationCategory,
  MatcherRule,
  RuleProblem,
  RuleSetBody,
} from "./types";
import { parsePattern } from "./rulePatterns";

export const STAGE_TYPES = ["active", "waiting", "completed"] as const;

export function moveItem<T>(list: T[], index: number, delta: number): T[] {
  const target = index + delta;
  if (index < 0 || index >= list.length || target < 0 || target >= list.length) {
    return list;
  }
  const next = [...list];
  const [item] = next.splice(index, 1);
  next.splice(target, 0, item);
  return next;
}

export function updateAt<T>(list: T[], index: number, patch: Partial<T>): T[] {
  return list.map((item, i) => (i === index ? { ...item, ...patch } : item));
}

export function removeAt<T>(list: T[], index: number): T[] {
  return list.filter((_, i) => i !== index);
}

export function getCategory(rule: RuleSetBody, name: string): MatcherRule[] {
  return rule.classification.find((c) => c.name === name)?.values ?? [];
}

export function setCategoryValues(
  rule: RuleSetBody,
  name: string,
  values: MatcherRule[],
): RuleSetBody {
  const exists = rule.classification.some((c) => c.name === name);
  const classification: ClassificationCategory[] = exists
    ? rule.classification.map((c) => (c.name === name ? { ...c, values } : c))
    : [...rule.classification, { name, values }];
  return { ...rule, classification };
}

function deepEqual(a: unknown, b: unknown): boolean {
  if (a === b) return true;
  if (typeof a !== "object" || typeof b !== "object" || a === null || b === null) {
    return false;
  }
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  if (Array.isArray(a) && Array.isArray(b)) {
    return a.length === b.length && a.every((item, i) => deepEqual(item, b[i]));
  }
  const left = a as Record<string, unknown>;
  const right = b as Record<string, unknown>;
  const keys = Object.keys(left);
  return (
    keys.length === Object.keys(right).length &&
    keys.every((key) => key in right && deepEqual(left[key], right[key]))
  );
}

export function isDirty(base: RuleSetBody, draft: RuleSetBody): boolean {
  return !deepEqual(base, draft);
}

function checkPatterns(
  patterns: string[],
  basePath: string,
  problems: RuleProblem[],
): void {
  patterns.forEach((raw, j) => {
    if (parsePattern(raw).value.trim() === "") {
      problems.push({ path: `${basePath}.${j}`, message: "Enter a value to match." });
    }
  });
}

function checkMatcherRules(
  rules: MatcherRule[],
  basePath: string,
  problems: RuleProblem[],
): void {
  const seen = new Set<string>();
  rules.forEach((rule, i) => {
    const name = rule.name.trim();
    if (name === "") {
      problems.push({ path: `${basePath}.${i}.name`, message: "Give this a name." });
    } else if (seen.has(name)) {
      problems.push({
        path: `${basePath}.${i}.name`,
        message: `"${name}" is already used. Names must be unique.`,
      });
    }
    seen.add(name);
    checkPatterns(rule.labels, `${basePath}.${i}.labels`, problems);
    checkPatterns(rule.title, `${basePath}.${i}.title`, problems);
  });
}

function checkThreshold(value: number, path: string, problems: RuleProblem[]): void {
  if (!Number.isInteger(value) || value < 1) {
    problems.push({ path, message: "Enter a whole number of days, 1 or more." });
  }
}

export interface RuleSetContext {
  otherDefaultExists: boolean;
  claimedBy: Record<number, string>;
  savedProjectIds: number[];
}

function sameIdSet(a: number[], b: number[]): boolean {
  const left = new Set(a);
  const right = new Set(b);
  return left.size === right.size && [...left].every((id) => right.has(id));
}

function claimedMessage(ids: number[], claimedBy: Record<number, string>): string | null {
  const parts = ids
    .filter((id) => claimedBy[id] !== undefined)
    .map((id, i) => (i === 0 ? `Project ${id} already belongs to ${claimedBy[id]}` : `Project ${id} to ${claimedBy[id]}`));
  if (parts.length === 0) return null;
  if (parts.length === 1) return `${parts[0]}.`;
  return `${parts.slice(0, -1).join(", ")}, and ${parts[parts.length - 1]}.`;
}

export function teamNameInUse(team: string, otherTeams: string[]): boolean {
  const wanted = team.trim().toLowerCase();
  return wanted !== "" && otherTeams.some((t) => t.trim().toLowerCase() === wanted);
}

export function validateRuleSet(rule: RuleSetBody, context?: RuleSetContext): RuleProblem[] {
  const problems: RuleProblem[] = [];

  if (rule.team.trim() === "") {
    problems.push({ path: "team", message: "Give this rule set a team name." });
  }
  if (context && !sameIdSet(rule.project_ids, context.savedProjectIds)) {
    if (rule.project_ids.length === 0 && context.otherDefaultExists) {
      problems.push({
        path: "project_ids",
        message:
          "Choose at least one project. Another rule set already covers all remaining projects.",
      });
    }
    const claimed = claimedMessage(rule.project_ids, context.claimedBy);
    if (claimed) problems.push({ path: "project_ids", message: claimed });
  }

  for (const category of rule.classification) {
    checkMatcherRules(category.values, `classification.${category.name}`, problems);
  }

  const seenStages = new Set<string>();
  rule.workflow.stages.forEach((stage, i) => {
    const name = stage.name.trim();
    if (name === "") {
      problems.push({ path: `workflow.stages.${i}.name`, message: "Give this stage a name." });
    } else if (seenStages.has(name)) {
      problems.push({
        path: `workflow.stages.${i}.name`,
        message: `"${name}" is already used. Stage names must be unique.`,
      });
    }
    seenStages.add(name);
    if (!(STAGE_TYPES as readonly string[]).includes(stage.type)) {
      problems.push({
        path: `workflow.stages.${i}.type`,
        message: "Choose Active, Waiting or Completed.",
      });
    }
    checkPatterns(stage.labels, `workflow.stages.${i}.labels`, problems);
  });

  checkMatcherRules(rule.contexts.rules, "contexts.rules", problems);

  for (const [type, patterns] of Object.entries(rule.validation.required_labels)) {
    checkPatterns(patterns, `validation.required_labels.${type}`, problems);
  }
  checkThreshold(
    rule.validation.stale_threshold_days,
    "validation.stale_threshold_days",
    problems,
  );
  checkThreshold(
    rule.validation.max_cycle_time_days,
    "validation.max_cycle_time_days",
    problems,
  );

  return problems;
}

export function problemsByPath(problems: RuleProblem[]): Record<string, string> {
  const lookup: Record<string, string> = {};
  for (const problem of problems) {
    if (!(problem.path in lookup)) lookup[problem.path] = problem.message;
  }
  return lookup;
}

export function problemsWithPrefix(
  lookup: Record<string, string>,
  prefix: string,
): Record<number, string> {
  const result: Record<number, string> = {};
  for (const [path, message] of Object.entries(lookup)) {
    if (!path.startsWith(`${prefix}.`)) continue;
    const index = Number(path.slice(prefix.length + 1).split(".")[0]);
    if (Number.isInteger(index) && !(index in result)) result[index] = message;
  }
  return result;
}

export function buildNewRuleSetBody(
  base: RuleSetBody,
  team: string,
  projectIds: number[],
): RuleSetBody {
  return { ...base, team: team.trim(), project_ids: projectIds };
}
