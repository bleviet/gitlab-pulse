import type { ReactNode } from "react";
import type { LabelInventoryItem } from "../../lib/labelInventory";
import { getCategory, setCategoryValues } from "../../lib/ruleDraft";
import type { RuleSetBody } from "../../lib/types";
import { ClassificationEditor } from "./ClassificationEditor";
import { ContextsEditor } from "./ContextsEditor";
import { QualityEditor } from "./QualityEditor";
import type { SectionId } from "./sections";
import { StagesEditor } from "./StagesEditor";
import type { SuggestSection } from "../../lib/ruleSuggestions";
import { SuggestFromLabels } from "./SuggestFromLabels";

interface SectionEditorProps {
  section: SectionId;
  rule: RuleSetBody;
  inventory: LabelInventoryItem[];
  problems: Record<string, string>;
  labelCounts?: Record<string, number>;
  titleCounts?: Record<string, number>;
  canEdit: boolean;
  onChange: (next: RuleSetBody) => void;
}

export function SectionEditor({
  section,
  rule,
  inventory,
  problems,
  labelCounts,
  titleCounts,
  canEdit,
  onChange,
}: SectionEditorProps) {
  const suggest = (target: SuggestSection): ReactNode => (
    <SuggestFromLabels
      section={target}
      rule={rule}
      inventory={inventory}
      canEdit={canEdit}
      onChange={onChange}
    />
  );
  switch (section) {
    case "type":
    case "severity":
    case "priority":
      return (
        <ClassificationEditor
          key={section}
          category={section}
          extraActions={suggest(section)}
          rows={getCategory(rule, section)}
          inventory={inventory}
          problems={problems}
          labelCounts={labelCounts}
          titleCounts={titleCounts}
          onChange={(values) => onChange(setCategoryValues(rule, section, values))}
        />
      );
    case "stages":
      return (
        <StagesEditor
          stages={rule.workflow.stages}
          extraActions={suggest("stages")}
          inventory={inventory}
          problems={problems}
          labelCounts={labelCounts}
          onChange={(stages) => onChange({ ...rule, workflow: { ...rule.workflow, stages } })}
        />
      );
    case "contexts":
      return (
        <ContextsEditor
          contexts={rule.contexts}
          inventory={inventory}
          problems={problems}
          labelCounts={labelCounts}
          titleCounts={titleCounts}
          onChange={(contexts) => onChange({ ...rule, contexts })}
        />
      );
    case "quality":
      return (
        <QualityEditor
          rule={rule}
          inventory={inventory}
          problems={problems}
          labelCounts={labelCounts}
          onChange={(validation) => onChange({ ...rule, validation })}
        />
      );
    case "colors":
    case "projects":
    case "history":
    case "text":
      return null;
  }
}
