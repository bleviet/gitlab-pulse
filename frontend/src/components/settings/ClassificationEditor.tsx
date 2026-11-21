import type { ReactNode } from "react";
import { Plus } from "lucide-react";
import type { LabelInventoryItem } from "../../lib/labelInventory";
import { moveItem, problemsWithPrefix, removeAt, updateAt } from "../../lib/ruleDraft";
import type { MatcherRule } from "../../lib/types";
import { MatcherInput } from "./MatcherInput";
import { RowControls } from "./RowControls";
import { TextField } from "./TextField";

export type ClassificationCategoryId = "type" | "severity" | "priority";

const COPY: Record<ClassificationCategoryId, { noun: string; add: string; empty: string }> = {
  type: {
    noun: "issue type",
    add: "Add issue type",
    empty: "No issue types yet. Issues will have no type.",
  },
  severity: {
    noun: "severity level",
    add: "Add severity level",
    empty: "No severity levels yet.",
  },
  priority: {
    noun: "priority level",
    add: "Add priority level",
    empty: "No priority levels yet.",
  },
};

interface ClassificationEditorProps {
  category: ClassificationCategoryId;
  rows: MatcherRule[];
  onChange: (next: MatcherRule[]) => void;
  inventory: LabelInventoryItem[];
  problems: Record<string, string>;
  labelCounts?: Record<string, number>;
  titleCounts?: Record<string, number>;
  extraActions?: ReactNode;
}

export function ClassificationEditor({
  category,
  rows,
  onChange,
  inventory,
  problems,
  labelCounts,
  titleCounts,
  extraActions,
}: ClassificationEditorProps) {
  const copy = COPY[category];
  const base = `classification.${category}`;

  return (
    <div className="settings-rows">
      {rows.length === 0 && <p className="settings-hint">{copy.empty}</p>}
      {rows.map((row, i) => {
        const id = `settings-${category}-${i}`;
        return (
          <div key={i} className="settings-row">
            <div className="settings-row-head">
              <span className="settings-row-index" aria-hidden="true">
                {i + 1}
              </span>
              <TextField
                id={`${id}-name`}
                label={`Name of ${copy.noun} ${i + 1}`}
                value={row.name}
                problem={problems[`${base}.${i}.name`]}
                onChange={(name) => onChange(updateAt(rows, i, { name }))}
              />
              <RowControls
                label={row.name}
                index={i}
                count={rows.length}
                onMove={(delta) => onChange(moveItem(rows, i, delta))}
                onRemove={() => onChange(removeAt(rows, i))}
              />
            </div>
            <div className="settings-field">
              <span className="settings-field-label">Applies when the issue has this label</span>
              <MatcherInput
                id={`${id}-labels`}
                kind="label"
                value={row.labels}
                inventory={inventory}
                matchCounts={labelCounts}
                ariaLabel={`Labels for ${row.name || `${copy.noun} ${i + 1}`}`}
                problems={problemsWithPrefix(problems, `${base}.${i}.labels`)}
                onChange={(labels) => onChange(updateAt(rows, i, { labels }))}
              />
            </div>
            {category === "type" && (
              <div className="settings-field">
                <span className="settings-field-label">Also recognise by words in the title</span>
                <MatcherInput
                  id={`${id}-title`}
                  kind="title"
                  value={row.title}
                  inventory={inventory}
                  matchCounts={titleCounts}
                  ariaLabel={`Title words for ${row.name || `${copy.noun} ${i + 1}`}`}
                  problems={problemsWithPrefix(problems, `${base}.${i}.title`)}
                  onChange={(title) => onChange(updateAt(rows, i, { title }))}
                />
              </div>
            )}
          </div>
        );
      })}
      <div className="settings-add-row">
        <button
          type="button"
          className="pulse-btn-secondary"
          onClick={() => onChange([...rows, { name: "", labels: [], title: [] }])}
        >
          <Plus size={14} />
          <span>{copy.add}</span>
        </button>
        {extraActions}
      </div>
    </div>
  );
}
