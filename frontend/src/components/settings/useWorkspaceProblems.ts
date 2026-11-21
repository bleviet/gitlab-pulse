import { useMemo } from "react";
import { problemsByPath, type RuleSetContext } from "../../lib/ruleDraft";
import type { RuleProblem, RuleSetBody, RuleSetsResponse } from "../../lib/types";
import { describeUnplacedProblem, sectionForPath, splitProblems, type SectionId } from "./sections";

export function useRuleContext(
  response: RuleSetsResponse | null,
  selectedName: string | null,
  savedProjectIds: number[],
): { claimedBy: Record<number, string>; ruleContext: RuleSetContext } {
  const claimedBy = useMemo(() => {
    const claims: Record<number, string> = {};
    for (const other of response?.rule_sets ?? []) {
      if (other.name === selectedName) continue;
      for (const id of other.rule.project_ids) claims[id] = other.rule.team || other.name;
    }
    return claims;
  }, [response, selectedName]);
  const ruleContext = useMemo(
    () => ({
      claimedBy,
      otherDefaultExists:
        response?.default_name != null && response.default_name !== selectedName,
      savedProjectIds,
    }),
    [claimedBy, response, selectedName, savedProjectIds],
  );
  return { claimedBy, ruleContext };
}

export function useProblemSummary(allProblems: RuleProblem[], draft: RuleSetBody | null) {
  const problems = useMemo(() => problemsByPath(allProblems), [allProblems]);
  const unplacedProblems = useMemo(
    () =>
      draft
        ? splitProblems(allProblems).unplaced.map((p) => describeUnplacedProblem(p, draft))
        : [],
    [allProblems, draft],
  );
  const problemCountBySection = useMemo(() => {
    const counts: Partial<Record<SectionId, number>> = {};
    for (const problem of allProblems) {
      const id = sectionForPath(problem.path);
      if (id) counts[id] = (counts[id] ?? 0) + 1;
    }
    return counts;
  }, [allProblems]);
  return { problems, unplacedProblems, problemCountBySection };
}
