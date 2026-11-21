import { useCallback, useMemo, useState } from "react";
import { fetchRules } from "../../lib/api";
import { isDirty } from "../../lib/ruleDraft";
import type { RuleProblem, RuleSetBody, RuleSetItem, RuleSetsResponse } from "../../lib/types";

export type LoadState = "loading" | "error" | "ready";

export function useRuleSetsData() {
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [response, setResponse] = useState<RuleSetsResponse | null>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [draft, setDraft] = useState<RuleSetBody | null>(null);
  const [serverProblems, setServerProblems] = useState<RuleProblem[]>([]);

  const selected: RuleSetItem | null = useMemo(
    () => response?.rule_sets.find((r) => r.name === selectedName) ?? null,
    [response, selectedName],
  );
  const dirty = Boolean(selected && draft && isDirty(selected.rule, draft));

  const load = useCallback(async (preferredName?: string | null, preferDefault = false) => {
    setLoadState("loading");
    setLoadError(null);
    try {
      const data = await fetchRules();
      const chosen =
        (preferDefault
          ? data.rule_sets.find((r) => r.name === data.default_name)
          : data.rule_sets.find((r) => r.name === preferredName)) ??
        data.rule_sets[0] ??
        null;
      setResponse(data);
      setSelectedName(chosen?.name ?? null);
      setDraft(chosen?.rule ?? null);
      setServerProblems([]);
      setLoadState("ready");
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Could not load the rules");
      setLoadState("error");
    }
  }, []);

  return {
    loadState,
    loadError,
    response,
    setResponse,
    selectedName,
    setSelectedName,
    draft,
    setDraft,
    serverProblems,
    setServerProblems,
    selected,
    dirty,
    load,
  };
}
