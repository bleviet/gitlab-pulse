import { useCallback, useEffect, useMemo, useState } from "react";
import { buildLabelInventory } from "../../lib/labelInventory";
import { buildProjectInventory } from "../../lib/projectInventory";
import { validateRuleSet } from "../../lib/ruleDraft";
import { mergeProblems } from "../../lib/ruleImpact";
import type {
  IssueItem,
  LabelStyle,
  PaletteDefaults,
  RuleSetBody,
  SectionId,
} from "../../lib/types";
import { runSave, type Notice } from "./saveFlow";
import { useRulePreview } from "./useRulePreview";
import { useRuleSetActions } from "./useRuleSetActions";
import { useRuleSetsData } from "./useRuleSetsData";
import { useProblemSummary, useRuleContext } from "./useWorkspaceProblems";

export type RulePopoverId =
  | "mix"
  | "stages"
  | "quality"
  | "contexts"
  | "impact"
  | "projects"
  | "colors"
  | "history"
  | "text";

export type MixSubTab = "priority" | "type";

export interface ActiveRulePopover {
  id: RulePopoverId;
  anchor: HTMLElement | null;
  placement: "right" | "bottom";
  subTab?: MixSubTab;
}

const NO_PROJECTS: number[] = [];
const NO_PALETTE: PaletteDefaults = { light: {}, dark: {} };

export function popoverForSection(section: SectionId): {
  id: RulePopoverId;
  subTab?: MixSubTab;
} {
  if (section === "priority" || section === "type") {
    return { id: "mix", subTab: section };
  }
  return { id: section };
}

interface UseRuleEditorInput {
  enabled: boolean;
  isAdmin: boolean;
  activeTeamFilter: string;
  issues: IssueItem[];
  labelStyles: Record<string, LabelStyle>;
  onReloadDashboard: () => Promise<void>;
}

export function useRuleEditor({
  enabled,
  isAdmin,
  activeTeamFilter,
  issues,
  labelStyles,
  onReloadDashboard,
}: UseRuleEditorInput) {
  const {
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
  } = useRuleSetsData();

  const [editMode, setEditMode] = useState(false);
  const [unlockPopoverOpen, setUnlockPopoverOpen] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);
  const [activePopover, setActivePopover] = useState<ActiveRulePopover | null>(null);
  const [newRuleSetOpen, setNewRuleSetOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState<Notice | null>(null);

  const canEdit = enabled && editMode && isAdmin && !sessionExpired;

  const inventory = useMemo(() => buildLabelInventory(issues, labelStyles), [issues, labelStyles]);
  const projectInventory = useMemo(() => buildProjectInventory(issues), [issues]);

  const { claimedBy, ruleContext } = useRuleContext(
    response,
    selectedName,
    selected?.rule.project_ids ?? NO_PROJECTS,
  );
  const defaultName = response?.default_name ?? null;
  const isDefault = selected !== null && selected.name === defaultName;
  const ruleSets = response?.rule_sets ?? [];
  const teamNames = ruleSets.map((r) => r.rule.team);
  const otherTeamNames = ruleSets
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
    setUnlockPopoverOpen(true);
  }, [preview.unauthorized]);

  useEffect(() => {
    if (!isAdmin && editMode) {
      setEditMode(false);
      setActivePopover(null);
      setNewRuleSetOpen(false);
    }
  }, [isAdmin, editMode]);

  const allProblems = useMemo(
    () => mergeProblems(clientProblems, serverProblems, preview.problems),
    [clientProblems, serverProblems, preview.problems],
  );
  const { problems, unplacedProblems, problemCountBySection } = useProblemSummary(
    allProblems,
    draft,
  );

  const handleSessionExpired = useCallback(() => {
    setSessionExpired(true);
    setUnlockPopoverOpen(true);
  }, []);

  const actions = useRuleSetActions({
    selected,
    load,
    onReloadDashboard,
    setNotice,
    onSessionExpired: handleSessionExpired,
  });

  const enterEditMode = useCallback(() => {
    setEditMode(true);
    setSessionExpired(false);
    setNotice(null);
    const preferred =
      activeTeamFilter !== "All"
        ? (ruleSets.find((r) => r.rule.team === activeTeamFilter)?.name ?? selectedName)
        : selectedName;
    void load(preferred);
  }, [activeTeamFilter, load, ruleSets, selectedName]);

  const exitEditMode = useCallback(() => {
    if (saving) return;
    if (dirty && !window.confirm("Discard unsaved changes?")) return;
    setEditMode(false);
    setActivePopover(null);
    setNewRuleSetOpen(false);
    setNotice(null);
    if (selected) {
      setDraft(selected.rule);
      setServerProblems([]);
    }
  }, [saving, dirty, selected, setDraft, setServerProblems]);

  const toggleEditMode = useCallback(() => {
    if (!enabled) return;
    if (editMode) {
      exitEditMode();
      return;
    }
    if (!isAdmin || sessionExpired) {
      setUnlockPopoverOpen((prev) => !prev);
      return;
    }
    enterEditMode();
  }, [enabled, editMode, exitEditMode, isAdmin, sessionExpired, enterEditMode]);

  const handleUnlocked = useCallback(() => {
    setUnlockPopoverOpen(false);
    setSessionExpired(false);
    if (!editMode) {
      enterEditMode();
    }
  }, [editMode, enterEditMode]);

  const openPopover = useCallback(
    (
      id: RulePopoverId,
      anchor: HTMLElement | null,
      placement: "right" | "bottom" = "bottom",
      subTab?: MixSubTab,
    ) => {
      setActivePopover((prev) => {
        if (prev && prev.id === id && prev.anchor === anchor && (!subTab || prev.subTab === subTab)) {
          return null;
        }
        return { id, anchor, placement, subTab: subTab ?? (id === "mix" ? "priority" : undefined) };
      });
    },
    [],
  );

  const closePopover = useCallback(() => {
    setActivePopover(null);
  }, []);

  const setMixSubTab = useCallback((subTab: MixSubTab) => {
    setActivePopover((prev) => (prev && prev.id === "mix" ? { ...prev, subTab } : prev));
  }, []);

  const focusSection = useCallback((section: SectionId) => {
    const target = popoverForSection(section);
    setActivePopover({
      id: target.id,
      anchor: null,
      placement: "bottom",
      subTab: target.subTab,
    });
  }, []);

  const updateDraft = useCallback(
    (next: RuleSetBody) => {
      setDraft(next);
      setServerProblems([]);
    },
    [setDraft, setServerProblems],
  );

  const handleSelectRuleSet = useCallback(
    (name: string) => {
      if (dirty && !window.confirm("Discard unsaved changes?")) return;
      const next = response?.rule_sets.find((r) => r.name === name);
      if (!next) return;
      setSelectedName(name);
      setDraft(next.rule);
      setServerProblems([]);
      setNotice(null);
    },
    [dirty, response, setSelectedName, setDraft, setServerProblems],
  );

  const handleDiscard = useCallback(() => {
    if (!selected) return;
    setDraft(selected.rule);
    setServerProblems([]);
    setNotice(null);
  }, [selected, setDraft, setServerProblems]);

  const handleSave = useCallback(async () => {
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
      setUnlockOpen: setUnlockPopoverOpen,
      setSection: focusSection,
      onReloadDashboard,
    });
  }, [selected, draft, setServerProblems, setResponse, setDraft, focusSection, onReloadDashboard]);

  const handleLoadVersion = useCallback(
    (rule: RuleSetBody, text: string) => {
      if (!draft) return;
      updateDraft({ ...rule, team: draft.team, project_ids: draft.project_ids });
      setNotice({ kind: "info", text });
    },
    [draft, updateDraft],
  );

  const handleCreateRuleSet = useCallback(
    async (team: string, projectIds: number[]) => {
      if (await actions.create(team, projectIds)) {
        setNewRuleSetOpen(false);
      }
    },
    [actions],
  );

  const openNewRuleSet = useCallback(() => {
    actions.resetCreate();
    setActivePopover(null);
    setNewRuleSetOpen(true);
  }, [actions]);

  return {
    editMode,
    canEdit,
    unlockPopoverOpen,
    setUnlockPopoverOpen,
    activePopover,
    openPopover,
    closePopover,
    setMixSubTab,
    newRuleSetOpen,
    setNewRuleSetOpen,
    openNewRuleSet,
    loadState,
    loadError,
    load,
    response,
    ruleSets,
    selected,
    selectedName,
    defaultName,
    isDefault,
    paletteDefaults: response?.palette_defaults ?? NO_PALETTE,
    draft,
    dirty,
    saving,
    notice,
    setNotice,
    inventory,
    projectInventory,
    claimedBy,
    teamNames,
    otherTeamNames,
    problems,
    allProblems,
    unplacedProblems,
    problemCountBySection,
    preview,
    actions,
    toggleEditMode,
    exitEditMode,
    handleUnlocked,
    updateDraft,
    handleSelectRuleSet,
    handleDiscard,
    handleSave,
    handleLoadVersion,
    handleCreateRuleSet,
  };
}
