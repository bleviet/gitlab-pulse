import { getCategory, setCategoryValues } from "../../lib/ruleDraft";
import { serializePattern } from "../../lib/rulePatterns";
import type { RuleProblem, RuleSetBody, SectionId } from "../../lib/types";

export type { SectionId };

export interface SectionInfo {
  id: SectionId;
  title: string;
  intro: string;
}

export const SECTIONS: SectionInfo[] = [
  {
    id: "type",
    title: "Issue types",
    intro:
      "Issue types sort issues into kinds such as Bug or Feature in charts and tables. Rows are checked from top to bottom and the first row that matches wins, so put the more specific types first.",
  },
  {
    id: "severity",
    title: "Severity",
    intro:
      "Severity says how serious a problem is. Rows are checked from top to bottom and the first row that matches wins, so order matters.",
  },
  {
    id: "priority",
    title: "Priority",
    intro:
      "Priority says how urgent an issue is. The first row that matches wins. The order is also the ranking order on the dashboard: the top row is the most urgent.",
  },
  {
    id: "stages",
    title: "Workflow stages",
    intro:
      "Stages are the columns of the board, in the order listed here. An issue sits in the first stage it matches. Closed issues always count as Done, and open issues that match no stage are shown as Backlog.",
  },
  {
    id: "contexts",
    title: "Contexts",
    intro:
      "Contexts group issues by product area, customer or team so you can narrow the dashboard to one of them. An issue can belong to several contexts, so order does not matter here.",
  },
  {
    id: "quality",
    title: "Quality checks",
    intro:
      "Quality checks flag issues that need attention, such as issues that went quiet, took too long, or are missing labels or fields.",
  },
];

export function sectionForPath(path: string): SectionId | null {
  const parts = path.split(".");
  if (parts[0] === "classification") {
    const category = parts[1];
    if (category === "type" || category === "severity" || category === "priority") {
      return category;
    }
    return null;
  }
  if (parts[0] === "workflow") return "stages";
  if (parts[0] === "contexts") return "contexts";
  if (parts[0] === "validation") return "quality";
  return null;
}

export function splitProblems(problems: RuleProblem[]): {
  placed: RuleProblem[];
  unplaced: RuleProblem[];
} {
  const placed: RuleProblem[] = [];
  const unplaced: RuleProblem[] = [];
  for (const problem of problems) {
    (sectionForPath(problem.path) ? placed : unplaced).push(problem);
  }
  return { placed, unplaced };
}

export function describeUnplacedProblem(problem: RuleProblem, rule: RuleSetBody): string {
  const [root, category, index] = problem.path.split(".");
  if (root !== "classification" || category === undefined) return problem.message;
  const value = rule.classification.find((c) => c.name === category)?.values[Number(index)];
  const subject = value?.name ? `${category} "${value.name}"` : category;
  return `${subject}: ${problem.message}`;
}

export function rowNamesForSection(rule: RuleSetBody, section: SectionId): string[] {
  switch (section) {
    case "type":
    case "severity":
    case "priority":
      return getCategory(rule, section).map((row) => row.name);
    case "stages":
      return rule.workflow.stages.map((stage) => stage.name);
    case "contexts":
      return rule.contexts.rules.map((row) => row.name);
    case "quality":
      return [];
  }
}

export function addLabelToRow(
  rule: RuleSetBody,
  section: SectionId,
  index: number,
  label: string,
): RuleSetBody {
  const pattern = serializePattern({ mode: "exact", value: label });
  const withLabel = <T extends { labels: string[] }>(rows: T[]): T[] =>
    rows.map((row, i) =>
      i === index && !row.labels.includes(pattern)
        ? { ...row, labels: [...row.labels, pattern] }
        : row,
    );
  switch (section) {
    case "type":
    case "severity":
    case "priority":
      return setCategoryValues(rule, section, withLabel(getCategory(rule, section)));
    case "stages":
      return { ...rule, workflow: { ...rule.workflow, stages: withLabel(rule.workflow.stages) } };
    case "contexts":
      return { ...rule, contexts: { ...rule.contexts, rules: withLabel(rule.contexts.rules) } };
    case "quality":
      return rule;
  }
}
