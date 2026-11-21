import type { LabelInventoryItem } from "../../lib/labelInventory";
import type { ProjectInfo } from "../../lib/projectInventory";
import { getCategory, setCategoryValues } from "../../lib/ruleDraft";
import type { SuggestSection } from "../../lib/ruleSuggestions";
import type {
  ImpactSummary,
  PaletteDefaults,
  RuleSaveResponse,
  RuleSetBody,
  RuleSetItem,
  ThemeMode,
} from "../../lib/types";
import { ClassificationEditor } from "./ClassificationEditor";
import { ColorsEditor } from "./ColorsEditor";
import { ContextsEditor } from "./ContextsEditor";
import { HistoryPanel } from "./HistoryPanel";
import { ProjectsEditor } from "./ProjectsEditor";
import { QualityEditor } from "./QualityEditor";
import { RulePopover } from "./RulePopover";
import { StagesEditor } from "./StagesEditor";
import { SuggestFromLabels } from "./SuggestFromLabels";
import { TextView } from "./TextView";
import type { ActiveRulePopover, MixSubTab, RulePopoverId } from "./useRuleEditor";

interface RuleEditorPopoverProps {
  active: ActiveRulePopover;
  draft: RuleSetBody;
  selected: RuleSetItem;
  isDefault: boolean;
  hasDefault: boolean;
  paletteDefaults: PaletteDefaults;
  theme: ThemeMode;
  otherTeamNames: string[];
  canEdit: boolean;
  dirty: boolean;
  saving: boolean;
  deleting: boolean;
  inventory: LabelInventoryItem[];
  projectInventory: ProjectInfo[];
  claimedBy: Record<number, string>;
  problems: Record<string, string>;
  impact: ImpactSummary | null;
  onChange: (next: RuleSetBody) => void;
  onChangeMixSubTab: (tab: MixSubTab) => void;
  onGoToDefault: () => void;
  onDelete: () => void;
  onLoadVersion: (rule: RuleSetBody, text: string) => void;
  onYamlSaved: (res: RuleSaveResponse) => Promise<void>;
  onSessionExpired: () => void;
  onReloadLatest: () => void;
  onClose: () => void;
}

const TITLES: Record<RulePopoverId, string> = {
  mix: "Open Mix Rules",
  stages: "Workflow Stages",
  quality: "Quality Signals",
  contexts: "Contexts",
  impact: "Impact",
  projects: "Team & Projects",
  colors: "Rule Colours",
  history: "Earlier Versions",
  text: "Edit YAML",
};

const SUBTITLES: Partial<Record<RulePopoverId, string>> = {
  mix: "First matching row wins. Order also sets priority rank.",
  stages: "Board columns in order. Unmatched open issues land in Backlog.",
  contexts: "Issues can belong to multiple contexts.",
  impact: "First matching row wins.",
};

export function RuleEditorPopover({
  active,
  draft,
  selected,
  isDefault,
  hasDefault,
  paletteDefaults,
  theme,
  otherTeamNames,
  canEdit,
  dirty,
  saving,
  deleting,
  inventory,
  projectInventory,
  claimedBy,
  problems,
  impact,
  onChange,
  onChangeMixSubTab,
  onGoToDefault,
  onDelete,
  onLoadVersion,
  onYamlSaved,
  onSessionExpired,
  onReloadLatest,
  onClose,
}: RuleEditorPopoverProps) {
  const mixTab: MixSubTab = active.subTab ?? "priority";

  const suggest = (target: SuggestSection) => (
    <SuggestFromLabels
      section={target}
      rule={draft}
      inventory={inventory}
      canEdit={canEdit}
      onChange={onChange}
    />
  );

  const headerExtra =
    active.id === "mix" ? (
      <div className="pulse-segmented compact" role="group" aria-label="Rule category">
        <button
          type="button"
          aria-pressed={mixTab === "priority"}
          onClick={() => onChangeMixSubTab("priority")}
        >
          Priority
        </button>
        <button
          type="button"
          aria-pressed={mixTab === "type"}
          onClick={() => onChangeMixSubTab("type")}
        >
          Types
        </button>
      </div>
    ) : undefined;

  const isWide = active.id === "colors" || active.id === "text";

  return (
    <RulePopover
      id={active.id}
      title={TITLES[active.id]}
      subtitle={SUBTITLES[active.id]}
      anchor={active.anchor}
      placement={active.placement}
      wide={isWide}
      headerExtra={headerExtra}
      onClose={onClose}
    >
      <fieldset
        className="settings-fieldset"
        disabled={
          (!canEdit || saving) &&
          !(active.id === "text" || (active.id === "colors" && !isDefault))
        }
      >
        {active.id === "mix" && (
          <ClassificationEditor
            key={mixTab}
            category={mixTab}
            rows={getCategory(draft, mixTab)}
            inventory={inventory}
            problems={problems}
            counts={mixTab === "priority" ? impact?.priorities : impact?.types}
            labelCounts={impact?.label_pattern_counts}
            titleCounts={impact?.title_pattern_counts}
            colors={draft.colors}
            paletteDefaults={paletteDefaults}
            theme={theme}
            canEditColors={isDefault && canEdit && !saving}
            onChangeColors={(colors) => onChange({ ...draft, colors })}
            extraActions={suggest(mixTab)}
            onChange={(values) => onChange(setCategoryValues(draft, mixTab, values))}
          />
        )}

        {active.id === "impact" && (
          <ClassificationEditor
            category="impact"
            rows={getCategory(draft, "impact")}
            inventory={inventory}
            problems={problems}
            counts={impact?.impacts}
            labelCounts={impact?.label_pattern_counts}
            colors={draft.colors}
            paletteDefaults={paletteDefaults}
            theme={theme}
            canEditColors={isDefault && canEdit && !saving}
            onChangeColors={(colors) => onChange({ ...draft, colors })}
            extraActions={suggest("impact")}
            onChange={(values) => onChange(setCategoryValues(draft, "impact", values))}
          />
        )}

        {active.id === "stages" && (
          <StagesEditor
            stages={draft.workflow.stages}
            inventory={inventory}
            problems={problems}
            counts={impact?.stages}
            labelCounts={impact?.label_pattern_counts}
            extraActions={suggest("stages")}
            onChange={(stages) => onChange({ ...draft, workflow: { ...draft.workflow, stages } })}
          />
        )}

        {active.id === "contexts" && (
          <ContextsEditor
            contexts={draft.contexts}
            inventory={inventory}
            problems={problems}
            counts={impact?.contexts}
            labelCounts={impact?.label_pattern_counts}
            titleCounts={impact?.title_pattern_counts}
            onChange={(contexts) => onChange({ ...draft, contexts })}
          />
        )}

        {active.id === "quality" && (
          <QualityEditor
            rule={draft}
            inventory={inventory}
            problems={problems}
            counts={impact?.quality}
            labelCounts={impact?.label_pattern_counts}
            onChange={(validation) => onChange({ ...draft, validation })}
          />
        )}

        {active.id === "projects" && (
          <ProjectsEditor
            rule={draft}
            isDefault={isDefault}
            hasDefault={hasDefault}
            otherTeamNames={otherTeamNames}
            inventory={projectInventory}
            claimedBy={claimedBy}
            problems={problems}
            deleteBlocked={dirty}
            deleting={deleting}
            onChange={onChange}
            onDelete={onDelete}
          />
        )}

        {active.id === "colors" && (
          <ColorsEditor
            rule={draft}
            defaults={paletteDefaults}
            problems={problems}
            isDefault={isDefault}
            canGoToDefault={hasDefault}
            readOnly={!canEdit || saving}
            switchLocked={saving}
            onGoToDefault={onGoToDefault}
            onChange={onChange}
          />
        )}

        {active.id === "history" && (
          <HistoryPanel
            name={selected.name}
            refreshKey={selected.revision}
            canEdit={canEdit}
            dirty={dirty}
            onLoadVersion={onLoadVersion}
          />
        )}

        {active.id === "text" && (
          <TextView
            name={selected.name}
            revision={selected.revision}
            canEdit={canEdit}
            dirty={dirty}
            onSaved={onYamlSaved}
            onSessionExpired={onSessionExpired}
            onReloadLatest={onReloadLatest}
          />
        )}
      </fieldset>
    </RulePopover>
  );
}
