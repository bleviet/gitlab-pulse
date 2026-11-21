import type { Dispatch, SetStateAction } from "react";
import { ApiError, saveRuleSet } from "../../lib/api";
import type {
  AdminJobResponse,
  RuleProblem,
  RuleSetBody,
  RuleSetItem,
  RuleSetsResponse,
} from "../../lib/types";
import { sectionForPath, type SectionId } from "./sections";

export interface Notice {
  kind: "success" | "warning" | "error" | "conflict" | "info";
  text: string;
  job?: AdminJobResponse;
}

export interface SaveDeps {
  selected: RuleSetItem;
  draft: RuleSetBody;
  setSaving: (saving: boolean) => void;
  setNotice: (notice: Notice | null) => void;
  setServerProblems: (problems: RuleProblem[]) => void;
  setResponse: Dispatch<SetStateAction<RuleSetsResponse | null>>;
  setDraft: (draft: RuleSetBody) => void;
  setSessionExpired: (expired: boolean) => void;
  setUnlockOpen: (open: boolean) => void;
  setSection: (section: SectionId) => void;
  onReloadDashboard: () => Promise<void>;
}

export async function runSave({
  selected,
  draft,
  setSaving,
  setNotice,
  setServerProblems,
  setResponse,
  setDraft,
  setSessionExpired,
  setUnlockOpen,
  setSection,
  onReloadDashboard,
}: SaveDeps): Promise<void> {
  setSaving(true);
  setNotice(null);
  setServerProblems([]);
  try {
    const res = await saveRuleSet(selected.name, selected.revision, draft);
    setResponse((prev) =>
      prev
        ? {
            ...prev,
            rule_sets: prev.rule_sets.map((r) => (r.name === res.rule_set.name ? res.rule_set : r)),
          }
        : prev,
    );
    setDraft(res.rule_set.rule);
    setSessionExpired(false);
    if (res.job.success) {
      try {
        await onReloadDashboard();
        setNotice({ kind: "success", text: "Saved. The dashboard has been recalculated." });
      } catch {
        setNotice({
          kind: "warning",
          text: "Saved and recalculated, but the dashboard could not be refreshed. Use the refresh button in the top bar.",
        });
      }
    } else {
      setNotice({
        kind: "warning",
        text: "Your rules were saved, but recalculating the dashboard failed.",
        job: res.job,
      });
    }
  } catch (err) {
    if (err instanceof ApiError && err.status === 422) {
      setServerProblems(err.problems);
      setNotice({ kind: "error", text: err.message });
      const first = err.problems.map((p) => sectionForPath(p.path)).find((s) => s !== null);
      if (first) setSection(first);
    } else if (err instanceof ApiError && err.status === 409) {
      setNotice({ kind: "conflict", text: err.message });
    } else if (err instanceof ApiError && err.status === 401) {
      setSessionExpired(true);
      setUnlockOpen(true);
      setNotice({ kind: "error", text: "Your session has ended. Unlock editing to save." });
    } else {
      setNotice({
        kind: "error",
        text: err instanceof Error ? err.message : "Saving failed",
      });
    }
  } finally {
    setSaving(false);
  }
}
