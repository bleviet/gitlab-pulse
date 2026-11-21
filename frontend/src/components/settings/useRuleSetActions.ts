import { useCallback, useState } from "react";
import { ApiError, createRuleSet, deleteRuleSet } from "../../lib/api";
import { buildNewRuleSetBody } from "../../lib/ruleDraft";
import type { AdminJobResponse, RuleProblem, RuleSetItem } from "../../lib/types";
import type { Notice } from "./saveFlow";

interface UseRuleSetActionsInput {
  selected: RuleSetItem | null;
  load: (preferredName: string | null, preferDefault?: boolean) => Promise<void>;
  onReloadDashboard: () => Promise<void>;
  setNotice: (notice: Notice | null) => void;
  onSessionExpired: () => void;
}

export function useRuleSetActions({
  selected,
  load,
  onReloadDashboard,
  setNotice,
  onSessionExpired,
}: UseRuleSetActionsInput) {
  const [busy, setBusy] = useState(false);
  const [createProblems, setCreateProblems] = useState<RuleProblem[]>([]);
  const [createError, setCreateError] = useState<string | null>(null);

  const resetCreate = useCallback(() => {
    setCreateProblems([]);
    setCreateError(null);
  }, []);

  const announce = useCallback(
    async (job: AdminJobResponse, successText: string, failureText: string) => {
      if (!job.success) {
        setNotice({ kind: "warning", text: failureText, job });
        return;
      }
      try {
        await onReloadDashboard();
        setNotice({ kind: "success", text: successText });
      } catch {
        setNotice({
          kind: "warning",
          text: "The rules were applied, but the dashboard could not be refreshed. Use the refresh button in the top bar.",
        });
      }
    },
    [onReloadDashboard, setNotice],
  );

  const create = useCallback(
    async (team: string, projectIds: number[]): Promise<boolean> => {
      if (!selected) return false;
      setBusy(true);
      resetCreate();
      try {
        const res = await createRuleSet(buildNewRuleSetBody(selected.rule, team, projectIds));
        await load(res.rule_set.name);
        await announce(
          res.job,
          "Created. The dashboard has been recalculated.",
          "The new rule set was created, but recalculating the dashboard failed.",
        );
        return true;
      } catch (err) {
        if (err instanceof ApiError && err.status === 401) onSessionExpired();
        setCreateProblems(err instanceof ApiError ? err.problems : []);
        setCreateError(err instanceof Error ? err.message : "Creating the rule set failed");
        return false;
      } finally {
        setBusy(false);
      }
    },
    [selected, load, announce, resetCreate, onSessionExpired],
  );

  const remove = useCallback(async () => {
    if (!selected) return;
    const confirmed = window.confirm(
      `Delete the rules of "${selected.rule.team}"? Its projects will use the default rules. This is applied immediately.`,
    );
    if (!confirmed) return;
    setBusy(true);
    setNotice(null);
    try {
      const res = await deleteRuleSet(selected.name, selected.revision);
      await load(null, true);
      await announce(
        res.job,
        "Deleted. The dashboard has been recalculated.",
        "The rule set was deleted, but recalculating the dashboard failed.",
      );
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setNotice({ kind: "conflict", text: err.message });
      } else if (err instanceof ApiError && err.status === 401) {
        onSessionExpired();
        setNotice({ kind: "error", text: "Your session has ended. Unlock editing to continue." });
      } else {
        setNotice({
          kind: "error",
          text: err instanceof Error ? err.message : "Deleting the rule set failed",
        });
      }
    } finally {
      setBusy(false);
    }
  }, [selected, load, announce, setNotice, onSessionExpired]);

  return { busy, createProblems, createError, resetCreate, create, remove };
}
