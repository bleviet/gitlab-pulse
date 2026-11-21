import { useState } from "react";
import { Plus } from "lucide-react";
import type { LabelInventoryItem } from "../../lib/labelInventory";
import { problemsWithPrefix, removeAt, updateAt } from "../../lib/ruleDraft";
import type { ContextsConfig, CountChange } from "../../lib/types";
import { MatcherInput } from "./MatcherInput";
import { RowControls } from "./RowControls";

interface ContextsEditorProps {
  contexts: ContextsConfig;
  onChange: (next: ContextsConfig) => void;
  inventory: LabelInventoryItem[];
  problems: Record<string, string>;
  counts?: CountChange[];
  labelCounts?: Record<string, number>;
  titleCounts?: Record<string, number>;
}

export function ContextsEditor({
  contexts,
  onChange,
  inventory,
  problems,
  counts,
  labelCounts,
  titleCounts,
}: ContextsEditorProps) {
  const [expandedTitles, setExpandedTitles] = useState<Record<number, boolean>>({});
  const rows = contexts.rules;
  const setRows = (next: typeof rows) => onChange({ ...contexts, rules: next });

  return (
    <div className="rule-compact-list">
      <label className="settings-check rule-check-strip">
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
        const nameProblem = problems[`contexts.rules.${i}.name`];
        const count = row.name.trim()
          ? counts?.find((c) => c.name?.toLowerCase() === row.name.trim().toLowerCase())
          : undefined;
        const delta = count ? count.after - count.before : 0;
        const showTitle = row.title.length > 0 || Boolean(expandedTitles[i]);

        return (
          <div key={i} className="rule-item">
            <div className="rule-item-head">
              <input
                id={`${id}-name`}
                type="text"
                className={`settings-input rule-name-input${nameProblem ? " error" : ""}`}
                aria-label={`Name of context ${i + 1}`}
                aria-invalid={nameProblem ? true : undefined}
                placeholder="Context name"
                value={row.name}
                onChange={(e) => setRows(updateAt(rows, i, { name: e.target.value }))}
              />
              {count && (
                <span className={`rule-count-pill${delta !== 0 ? " changed" : ""}`}>
                  {delta !== 0 ? `${count.before}→${count.after}` : count.after}
                </span>
              )}
              <RowControls
                label={row.name}
                index={i}
                count={rows.length}
                onRemove={() => setRows(removeAt(rows, i))}
              />
            </div>

            {nameProblem && (
              <p className="settings-error-text" role="alert">
                {nameProblem}
              </p>
            )}

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

            {showTitle ? (
              <div className="rule-sub-field">
                <span className="rule-sub-label">Title words</span>
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
            ) : (
              <button
                type="button"
                className="rule-inline-link"
                onClick={() => setExpandedTitles((prev) => ({ ...prev, [i]: true }))}
              >
                + Match title words
              </button>
            )}
          </div>
        );
      })}

      <div className="rule-list-footer">
        <button
          type="button"
          className="pulse-btn-secondary settings-btn-small"
          onClick={() => setRows([...rows, { name: "", labels: [], title: [] }])}
        >
          <Plus size={13} />
          <span>Add context</span>
        </button>
      </div>
    </div>
  );
}
