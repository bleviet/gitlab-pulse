import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Lock, X } from "lucide-react";
import { ApiError, fetchRules, saveRuleSet } from "../../lib/api";
import { buildLabelInventory } from "../../lib/labelInventory";
import { isDirty, problemsByPath, validateRuleSet } from "../../lib/ruleDraft";
import type {
  AdminJobResponse,
  IssueItem,
  LabelStyle,
  RuleProblem,
  RuleSetBody,
  RuleSetItem,
  RuleSetsResponse,
} from "../../lib/types";
import { SaveBar } from "./SaveBar";
import { SectionEditor } from "./SectionEditor";
import { describeUnplacedProblem, SECTIONS, sectionForPath, splitProblems, type SectionId } from "./sections";
import { UnlockForm } from "./UnlockForm";

interface SettingsWorkspaceProps {
  open: boolean;
  isAdmin: boolean;
  issues: IssueItem[];
  labelStyles: Record<string, LabelStyle>;
  onClose: () => void;
  onLogin: (password: string) => Promise<void>;
  onReloadDashboard: () => Promise<void>;
}

interface Notice {
  kind: "success" | "warning" | "error" | "conflict";
  text: string;
  job?: AdminJobResponse;
}

type LoadState = "loading" | "error" | "ready";

function scopeText(rule: RuleSetBody): string {
  const count = rule.project_ids.length;
  if (count === 0) return "Applies to all projects";
  return `Applies to ${count} ${count === 1 ? "project" : "projects"}`;
}

export function SettingsWorkspace({
  open,
  isAdmin,
  issues,
  labelStyles,
  onClose,
  onLogin,
  onReloadDashboard,
}: SettingsWorkspaceProps) {
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [response, setResponse] = useState<RuleSetsResponse | null>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [draft, setDraft] = useState<RuleSetBody | null>(null);
  const [serverProblems, setServerProblems] = useState<RuleProblem[]>([]);
  const [section, setSection] = useState<SectionId>("type");
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [unlockOpen, setUnlockOpen] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);

  const dialogRef = useRef<HTMLDivElement | null>(null);

  const selected: RuleSetItem | null = useMemo(
    () => response?.rule_sets.find((r) => r.name === selectedName) ?? null,
    [response, selectedName],
  );
  const dirty = Boolean(selected && draft && isDirty(selected.rule, draft));

  const inventory = useMemo(() => buildLabelInventory(issues, labelStyles), [issues, labelStyles]);

  const clientProblems = useMemo(() => (draft ? validateRuleSet(draft) : []), [draft]);
  const allProblems = useMemo(
    () => [...clientProblems, ...serverProblems],
    [clientProblems, serverProblems],
  );
  const problems = useMemo(() => problemsByPath(allProblems), [allProblems]);

  const unplacedProblems = useMemo(
    () => (draft ? splitProblems(allProblems).unplaced.map((p) => describeUnplacedProblem(p, draft)) : []),
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

  const load = useCallback(async (preferredName?: string | null) => {
    setLoadState("loading");
    setLoadError(null);
    try {
      const data = await fetchRules();
      const chosen =
        data.rule_sets.find((r) => r.name === preferredName) ?? data.rule_sets[0] ?? null;
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

  useEffect(() => {
    if (!open) return;
    setNotice(null);
    setUnlockOpen(false);
    setSessionExpired(false);
    setSection("type");
    void load(null);
    const previouslyFocused = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();
    return () => previouslyFocused?.focus();
  }, [open, load]);

  const requestClose = useCallback(() => {
    if (saving) return;
    if (dirty && !window.confirm("Discard unsaved changes?")) return;
    onClose();
  }, [saving, dirty, onClose]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !e.defaultPrevented) requestClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, requestClose]);

  if (!open) return null;

  const updateDraft = (next: RuleSetBody) => {
    setDraft(next);
    setServerProblems([]);
  };

  const handleSelectRuleSet = (name: string) => {
    if (dirty && !window.confirm("Discard unsaved changes?")) return;
    const next = response?.rule_sets.find((r) => r.name === name);
    if (!next) return;
    setSelectedName(name);
    setDraft(next.rule);
    setServerProblems([]);
    setNotice(null);
  };

  const handleDiscard = () => {
    if (!selected) return;
    setDraft(selected.rule);
    setServerProblems([]);
    setNotice(null);
  };

  const handleSave = async () => {
    if (!selected || !draft) return;
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
  };

  const current = SECTIONS.find((s) => s.id === section) ?? SECTIONS[0];
  const loadErrorNames = Object.keys(response?.load_errors ?? {});
  const canEdit = isAdmin && !sessionExpired;
  const showUnlockBanner = !canEdit;
  const loadErrorNotice = `${loadErrorNames.length} rule ${loadErrorNames.length === 1 ? "file" : "files"} could not be read and ${loadErrorNames.length === 1 ? "is" : "are"} ignored: ${loadErrorNames.join(", ")}`;

  return (
    <div className="settings-overlay">
      <div
        ref={dialogRef}
        className="settings-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        tabIndex={-1}
      >
        <header className="settings-header">
          <h2 id="settings-title" className="settings-title">
            Settings
          </h2>
          {selected && (
            <div className="settings-header-meta">
              {response && response.rule_sets.length > 1 && (
                <>
                  <label htmlFor="settings-rule-set" className="settings-visually-hidden">
                    Rule set
                  </label>
                  <select
                    id="settings-rule-set"
                    className="settings-select"
                    value={selected.name}
                    onChange={(e) => handleSelectRuleSet(e.target.value)}
                  >
                    {response.rule_sets.map((r) => (
                      <option key={r.name} value={r.name}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </>
              )}
              <span className="settings-meta-text">
                Team: {selected.rule.team || "Not set"} · {scopeText(selected.rule)}
              </span>
            </div>
          )}
          <button
            type="button"
            className="pulse-icon-btn"
            aria-label="Close settings"
            onClick={requestClose}
          >
            <X size={15} />
          </button>
        </header>

        {loadState === "loading" && <div className="settings-state">Loading rules…</div>}

        {loadState === "error" && (
          <div className="settings-state settings-state-error" role="alert">
            <span>{loadError}</span>
            <button type="button" className="pulse-btn-secondary" onClick={() => void load(selectedName)}>
              Retry
            </button>
          </div>
        )}

        {loadState === "ready" && !draft && (
          <div className="settings-state">
            {loadErrorNames.length > 0 ? loadErrorNotice : "No rules were found."}
          </div>
        )}

        {loadState === "ready" && draft && (
          <>
            <div className="settings-body">
              <nav className="settings-nav" aria-label="Settings sections">
                {SECTIONS.map((s) => {
                  const count = problemCountBySection[s.id] ?? 0;
                  return (
                    <button
                      key={s.id}
                      type="button"
                      className="settings-nav-item"
                      aria-current={s.id === section ? "page" : undefined}
                      onClick={() => setSection(s.id)}
                    >
                      <span>{s.title}</span>
                      {count > 0 && (
                        <span className="settings-nav-badge" aria-label={`${count} problems`}>
                          {count}
                        </span>
                      )}
                    </button>
                  );
                })}
              </nav>

              <div className="settings-editor">
                {loadErrorNames.length > 0 && (
                  <div className="settings-notice warning" role="status">
                    {loadErrorNotice}
                  </div>
                )}

                {showUnlockBanner && (
                  <div className="settings-notice info">
                    <div className="settings-notice-row">
                      <Lock size={14} aria-hidden="true" />
                      <strong>View only</strong>
                      <span>You can look at the rules, but editing needs the admin password.</span>
                      {!unlockOpen && (
                        <button
                          type="button"
                          className="pulse-btn-secondary"
                          onClick={() => setUnlockOpen(true)}
                        >
                          Unlock editing
                        </button>
                      )}
                    </div>
                    {unlockOpen && (
                      <UnlockForm
                        onLogin={onLogin}
                        onDone={() => {
                          setUnlockOpen(false);
                          setSessionExpired(false);
                        }}
                      />
                    )}
                  </div>
                )}

                {notice && (
                  <div
                    className={`settings-notice ${notice.kind === "success" ? "success" : notice.kind === "error" ? "error" : "warning"}`}
                    role={notice.kind === "success" ? "status" : "alert"}
                  >
                    <div className="settings-notice-row">
                      <span>{notice.text}</span>
                      {notice.kind === "conflict" && (
                        <button
                          type="button"
                          className="pulse-btn-secondary"
                          onClick={() => {
                            setNotice(null);
                            void load(selectedName);
                          }}
                        >
                          Reload latest
                        </button>
                      )}
                    </div>
                    {notice.job?.stdout && <pre className="admin-log">{notice.job.stdout}</pre>}
                    {notice.job?.stderr && <pre className="admin-log">{notice.job.stderr}</pre>}
                  </div>
                )}

                {unplacedProblems.length > 0 && (
                  <div className="settings-notice error" role="alert">
                    <strong>These rules have problems that cannot be fixed on this screen:</strong>
                    <ul className="settings-problem-list">
                      {unplacedProblems.map((text, i) => (
                        <li key={i}>{text}</li>
                      ))}
                    </ul>
                    <span>Ask the person who maintains the rule files to correct them.</span>
                  </div>
                )}

                <h3 className="settings-section-title">{current.title}</h3>
                <p className="settings-intro">{current.intro}</p>

                <fieldset className="settings-fieldset" disabled={!canEdit || saving}>
                  <legend className="settings-visually-hidden">{current.title}</legend>
                  <SectionEditor
                    section={section}
                    rule={draft}
                    inventory={inventory}
                    problems={problems}
                    onChange={updateDraft}
                  />
                </fieldset>
              </div>
            </div>

            <SaveBar
              dirty={dirty}
              isAdmin={canEdit}
              saving={saving}
              problemCount={allProblems.length}
              onDiscard={handleDiscard}
              onSave={() => void handleSave()}
            />
          </>
        )}
      </div>
    </div>
  );
}
