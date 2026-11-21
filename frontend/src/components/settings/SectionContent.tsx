import type { LabelInventoryItem } from "../../lib/labelInventory";
import type { ProjectInfo } from "../../lib/projectInventory";
import type { RuleSetBody, RuleSetItem } from "../../lib/types";
import { HistoryPanel } from "./HistoryPanel";
import { ProjectsEditor } from "./ProjectsEditor";
import type { SectionId } from "./sections";
import { SectionEditor } from "./SectionEditor";

interface SectionContentProps {
  section: SectionId;
  draft: RuleSetBody;
  selected: RuleSetItem | null;
  isDefault: boolean;
  hasDefault: boolean;
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
      onChange={onChange}
    />
  );
}
