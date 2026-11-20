import { Plus } from "lucide-react";
import type { LabelInventoryItem } from "../../lib/labelInventory";
import { problemsWithPrefix, removeAt, updateAt } from "../../lib/ruleDraft";
import type { ContextsConfig } from "../../lib/types";
import { MatcherInput } from "./MatcherInput";
import { RowControls } from "./RowControls";
import { TextField } from "./TextField";

interface ContextsEditorProps {
  contexts: ContextsConfig;
  onChange: (next: ContextsConfig) => void;
  inventory: LabelInventoryItem[];
  problems: Record<string, string>;
  labelCounts?: Record<string, number>;
  titleCounts?: Record<string, number>;
}

export function ContextsEditor({ contexts, onChange, inventory, problems, labelCounts, titleCounts }: ContextsEditorProps) {
  const rows = contexts.rules;
  const setRows = (next: typeof rows) => onChange({ ...contexts, rules: next });

  return (
    <div className="settings-rows">
      <label className="settings-check settings-check-wide">
        <input
          type="checkbox"
          checked={contexts.require_assignment}
          onChange={(e) => onChange({ ...contexts, require_assignment: e.target.checked })}
        />
        <span>Flag issues that belong to no context</span>
      </label>

      {rows.length === 0 && <p className="settings-hint">No contexts yet.</p>}
      {rows.map((row, i) => {
        const id = `settings-context-${i}`;
        return (
          <div key={i} className="settings-row">
            <div className="settings-row-head">
              <span className="settings-row-index" aria-hidden="true">
                {i + 1}
              </span>
              <TextField
                id={`${id}-name`}
                label={`Name of context ${i + 1}`}
                value={row.name}
                problem={problems[`contexts.rules.${i}.name`]}
                onChange={(name) => setRows(updateAt(rows, i, { name }))}
              />
              <RowControls
                label={row.name}
                index={i}
                count={rows.length}
                onRemove={() => setRows(removeAt(rows, i))}
              />
            </div>
            <div className="settings-field">
              <span className="settings-field-label">Issue belongs here when it has this label</span>
              <MatcherInput
                id={`${id}-labels`}
                kind="label"
                value={row.labels}
                inventory={inventory}
                matchCounts={labelCounts}
                ariaLabel={`Labels for context ${row.name || i + 1}`}
                problems={problemsWithPrefix(problems, `contexts.rules.${i}.labels`)}
                onChange={(labels) => setRows(updateAt(rows, i, { labels }))}
              />
            </div>
            <div className="settings-field">
              <span className="settings-field-label">Or when the title has these words</span>
              <MatcherInput
                id={`${id}-title`}
                kind="title"
                value={row.title}
                inventory={inventory}
                matchCounts={titleCounts}
                ariaLabel={`Title words for context ${row.name || i + 1}`}
                problems={problemsWithPrefix(problems, `contexts.rules.${i}.title`)}
                onChange={(title) => setRows(updateAt(rows, i, { title }))}
              />
            </div>
          </div>
        );
      })}
      <button
        type="button"
        className="pulse-btn-secondary settings-add-btn"
        onClick={() => setRows([...rows, { name: "", labels: [], title: [] }])}
      >
        <Plus size={14} />
        <span>Add context</span>
      </button>
    </div>
  );
}
