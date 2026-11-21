import type { LabelInventoryItem } from "../../lib/labelInventory";
import type { ProjectInfo } from "../../lib/projectInventory";
import type { PaletteDefaults, RuleSetBody, RuleSetItem } from "../../lib/types";
import { ColorsEditor } from "./ColorsEditor";
import { HistoryPanel } from "./HistoryPanel";
import { ProjectsEditor } from "./ProjectsEditor";
import type { SectionId } from "./sections";
import { SectionEditor } from "./SectionEditor";
import { TextView } from "./TextView";

interface SectionContentProps {
  section: SectionId;
  draft: RuleSetBody;
  selected: RuleSetItem | null;
  isDefault: boolean;
  hasDefault: boolean;
  paletteDefaults: PaletteDefaults;
  onGoToDefault: () => void;
  otherTeamNames: string[];
  canEdit: boolean;
  dirty: boolean;
  inventory: LabelInventoryItem[];
  projectInventory: ProjectInfo[];
  claimedBy: Record<number, string>;
  problems: Record<string, string>;
  labelCounts?: Record<string, number>;
  titleCounts?: Record<string, number>;
  deleting: boolean;
  readOnly: boolean;
  saving: boolean;
  onChange: (next: RuleSetBody) => void;
  onDelete: () => void;
  onLoadVersion: (rule: RuleSetBody, description: string) => void;
}

export function SectionContent({
  section,
  draft,
  selected,
  isDefault,
  hasDefault,
  paletteDefaults,
  onGoToDefault,
  otherTeamNames,
  canEdit,
  dirty,
  inventory,
  projectInventory,
  claimedBy,
  problems,
  labelCounts,
  titleCounts,
  deleting,
  readOnly,
  saving,
  onChange,
  onDelete,
  onLoadVersion,
}: SectionContentProps) {
  if (section === "projects") {
    return (
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
    );
  }
  if (section === "colors") {
    return (
      <ColorsEditor
        rule={draft}
        defaults={paletteDefaults}
        problems={problems}
        isDefault={isDefault}
        canGoToDefault={hasDefault}
        readOnly={readOnly}
        switchLocked={saving}
        onGoToDefault={onGoToDefault}
        onChange={onChange}
      />
    );
  }
  if (section === "text") {
    return selected ? <TextView name={selected.name} refreshKey={selected.revision} dirty={dirty} /> : null;
  }
  if (section === "history") {
    return selected ? (
      <HistoryPanel
        name={selected.name}
        refreshKey={selected.revision}
        canEdit={canEdit}
        dirty={dirty}
        onLoadVersion={onLoadVersion}
      />
    ) : null;
  }
  return (
    <SectionEditor
      section={section}
      rule={draft}
      inventory={inventory}
      problems={problems}
      labelCounts={labelCounts}
      titleCounts={titleCounts}
      canEdit={canEdit}
      onChange={onChange}
    />
  );
}
