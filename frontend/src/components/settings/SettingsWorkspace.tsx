import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchRules } from "../../lib/api";
import { buildLabelInventory } from "../../lib/labelInventory";
import { buildProjectInventory } from "../../lib/projectInventory";
import { isDirty, validateRuleSet } from "../../lib/ruleDraft";
import { mergeProblems } from "../../lib/ruleImpact";
import type {
  IssueItem,
  LabelStyle,
  RuleProblem,
  RuleSetBody,
  RuleSetItem,
  RuleSetsResponse,
} from "../../lib/types";
import { ImpactPanel } from "./ImpactPanel";
import { NewRuleSetDialog } from "./NewRuleSetDialog";
import { SaveBar } from "./SaveBar";
import { SectionContent } from "./SectionContent";
import {
  addLabelToRow,
  rowNamesForSection,
  SECTIONS,
  type SectionId,
} from "./sections";
import { runSave } from "./saveFlow";
import { SettingsHeader } from "./SettingsHeader";
import { SettingsNav } from "./SettingsNav";
import { SettingsNotices, type Notice } from "./SettingsNotices";
import { useRuleSetActions } from "./useRuleSetActions";
import { useProblemSummary, useRuleContext } from "./useWorkspaceProblems";
import { useRulePreview } from "./useRulePreview";

interface SettingsWorkspaceProps {
  open: boolean;
  isAdmin: boolean;
  issues: IssueItem[];
  labelStyles: Record<string, LabelStyle>;
  onClose: () => void;
  onLogin: (password: string) => Promise<void>;
  onReloadDashboard: () => Promise<void>;
}

const NO_PROJECTS: number[] = [];

type LoadState = "loading" | "error" | "ready";

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

  const canEdit = isAdmin && !sessionExpired;

  const projectInventory = useMemo(() => buildProjectInventory(issues), [issues]);
  const { claimedBy, ruleContext } = useRuleContext(
    response,
    selectedName,
    selected?.rule.project_ids ?? NO_PROJECTS,
  );
  const defaultName = response?.default_name ?? null;
  const isDefault = selected !== null && selected.name === defaultName;
  const teamNames = (response?.rule_sets ?? []).map((r) => r.rule.team);
  const otherTeamNames = (response?.rule_sets ?? [])
    .filter((r) => r.name !== selectedName)
    .map((r) => r.rule.team);
  const clientProblems = useMemo(
    () => (draft ? validateRuleSet(draft, ruleContext) : []),
    [draft, ruleContext],
  );
  const preview = useRulePreview({
    enabled: canEdit && loadState === "ready" && !!selected && clientProblems.length === 0,
    name: selectedName,
    draft,
  });

  useEffect(() => {
    if (!preview.unauthorized) return;
    setSessionExpired(true);
    setUnlockOpen(true);
  }, [preview.unauthorized]);

  const allProblems = useMemo(
    () => mergeProblems(clientProblems, serverProblems, preview.problems),
    [clientProblems, serverProblems, preview.problems],
  );
  const { problems, unplacedProblems, problemCountBySection } = useProblemSummary(allProblems, draft);

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

  const [newOpen, setNewOpen] = useState(false);
  const handleSessionExpired = useCallback(() => {
    setSessionExpired(true);
    setUnlockOpen(true);
  }, []);
  const actions = useRuleSetActions({
    selected,
    load,
    onReloadDashboard,
    setNotice,
    onSessionExpired: handleSessionExpired,
  });

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
    await runSave({
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
    });
  };

  const current = SECTIONS.find((s) => s.id === section) ?? SECTIONS[0];
  const loadErrorNames = Object.keys(response?.load_errors ?? {});
  const loadErrorNotice =
    loadErrorNames.length === 0
      ? null
      : `${loadErrorNames.length} rule ${loadErrorNames.length === 1 ? "file" : "files"} could not be read and ${loadErrorNames.length === 1 ? "is" : "are"} ignored: ${loadErrorNames.join(", ")}`;

  const handleLoadVersion = (rule: RuleSetBody, text: string) => {
    if (!draft) return;
    updateDraft({ ...rule, team: draft.team, project_ids: draft.project_ids });
    setNotice({ kind: "info", text });
  };

  const handleCreate = async (team: string, projectIds: number[]) => {
    if (await actions.create(team, projectIds)) setNewOpen(false);
  };

  const handleQuickAdd = (label: string, rowIndex: number) => {
    if (draft) updateDraft(addLabelToRow(draft, section, rowIndex, label));
  };

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
        <SettingsHeader
          selected={selected}
          ruleSets={response?.rule_sets ?? []}
          canEdit={canEdit}
          defaultName={defaultName}
          newBlocked={dirty}
          onNewRuleSet={() => {
            actions.resetCreate();
            setNewOpen(true);
          }}
          onSelectRuleSet={handleSelectRuleSet}
          onClose={requestClose}
        />

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
          <div className="settings-state">{loadErrorNotice ?? "No rules were found."}</div>
        )}

        {loadState === "ready" && draft && (
          <>
            <div className="settings-body">
              <SettingsNav section={section} problemCounts={problemCountBySection} onSelect={setSection} />

              <div className="settings-main">
                <div className="settings-editor-head">
                  <SettingsNotices
                    loadErrorNotice={loadErrorNotice}
                    showUnlockBanner={!canEdit}
                    unlockOpen={unlockOpen}
                    onOpenUnlock={() => setUnlockOpen(true)}
                    onLogin={onLogin}
                    onUnlocked={() => {
                      setUnlockOpen(false);
                      setSessionExpired(false);
                    }}
                    notice={notice}
                    onReloadLatest={() => {
                      setNotice(null);
                      void load(selectedName);
                    }}
                    unplacedProblems={unplacedProblems}
                  />

                  <h3 className="settings-section-title">{current.title}</h3>
                  <p className="settings-intro">{current.intro}</p>
                </div>

                <ImpactPanel
                  section={section}
                  canEdit={canEdit}
                  dirty={dirty}
                  saving={saving}
                  hasClientProblems={clientProblems.length > 0}
                  preview={preview}
                  inventory={inventory}
                  rowNames={rowNamesForSection(draft, section)}
                  onQuickAdd={handleQuickAdd}
                />

                <fieldset className="settings-fieldset" disabled={!canEdit || saving}>
                  <legend className="settings-visually-hidden">{current.title}</legend>
                  <SectionContent
                    section={section}
                    draft={draft}
                    selected={selected}
                    isDefault={isDefault}
                    hasDefault={defaultName !== null}
                    otherTeamNames={otherTeamNames}
                    canEdit={canEdit}
                    dirty={dirty}
                    inventory={inventory}
                    projectInventory={projectInventory}
                    claimedBy={claimedBy}
                    problems={problems}
                    labelCounts={preview.impact?.label_pattern_counts}
                    titleCounts={preview.impact?.title_pattern_counts}
                    deleting={actions.busy}
                    onChange={updateDraft}
                    onDelete={() => void actions.remove()}
                    onLoadVersion={handleLoadVersion}
                  />
                </fieldset>
              </div>
            </div>

            {newOpen && selected && (
              <NewRuleSetDialog
                projects={projectInventory}
                claimedBy={{ ...claimedBy, ...Object.fromEntries(selected.rule.project_ids.map((id) => [id, selected.rule.team || selected.name])) }}
                sourceLabel={isDefault ? "the default rules" : `the rules of ${selected.rule.team}`}
                teamNames={teamNames}
                busy={actions.busy}
                problems={actions.createProblems}
                error={actions.createError}
                onCreate={(team, ids) => void handleCreate(team, ids)}
                onClose={() => setNewOpen(false)}
              />
            )}

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
