import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, previewRuleSet } from "../../lib/api";
import type { ImpactSummary, RuleProblem, RuleSetBody } from "../../lib/types";

export const PREVIEW_DEBOUNCE_MS = 600;

export interface RulePreviewState {
  status: "idle" | "loading" | "ready" | "error";
  impact: ImpactSummary | null;
  problems: RuleProblem[];
  error: string | null;
  unauthorized: boolean;
  resolvedDraft: RuleSetBody | null;
}

interface UseRulePreviewInput {
  enabled: boolean;
  name: string | null;
  draft: RuleSetBody | null;
}

export type RulePreview = RulePreviewState & { pending: boolean; retry: () => void };

const IDLE: RulePreviewState = {
  status: "idle",
  impact: null,
  problems: [],
  error: null,
  unauthorized: false,
  resolvedDraft: null,
};

export function useRulePreview({ enabled, name, draft }: UseRulePreviewInput): RulePreview {
  const [state, setState] = useState<RulePreviewState>(IDLE);
  const [retryCount, setRetryCount] = useState(0);
  const requestId = useRef(0);
  const startedFor = useRef<string | null>(null);

  useEffect(() => {
    if (!enabled || !name || !draft) {
      startedFor.current = null;
      setState(IDLE);
      return;
    }
    if (startedFor.current !== name) setState(IDLE);
    const delay = startedFor.current === name ? PREVIEW_DEBOUNCE_MS : 0;
    startedFor.current = name;
    const id = ++requestId.current;
    const controller = new AbortController();

    const timer = setTimeout(() => {
      setState((prev) => ({ ...prev, status: "loading", error: null, unauthorized: false }));
      previewRuleSet(name, draft, controller.signal)
        .then((res) => {
          if (id !== requestId.current) return;
          setState({
            status: "ready",
            impact: res.impact,
            problems: res.problems,
            error: null,
            unauthorized: false,
            resolvedDraft: draft,
          });
        })
        .catch((err: unknown) => {
          if (id !== requestId.current || controller.signal.aborted) return;
          setState((prev) => ({
            ...prev,
            status: "error",
            problems: [],
            error: err instanceof Error ? err.message : "Could not calculate the effect",
            unauthorized: err instanceof ApiError && err.status === 401,
          }));
        });
    }, delay);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [enabled, name, draft, retryCount]);

  const retry = useCallback(() => setRetryCount((n) => n + 1), []);

  const pending = enabled && draft !== null && state.resolvedDraft !== draft;
  return { ...state, pending, retry };
}
