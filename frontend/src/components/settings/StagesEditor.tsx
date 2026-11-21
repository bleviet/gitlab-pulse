import { useState, type ReactNode } from "react";
import { Plus } from "lucide-react";
import type { LabelInventoryItem } from "../../lib/labelInventory";
import { moveItem, problemsWithPrefix, removeAt, STAGE_TYPES, updateAt } from "../../lib/ruleDraft";
import type { CountChange, WorkflowStage } from "../../lib/types";
import { MatcherInput } from "./MatcherInput";
import { RowControls } from "./RowControls";

const STAGE_KINDS: Array<{ value: (typeof STAGE_TYPES)[number]; label: string }> = [
  { value: "active", label: "Active" },
  { value: "waiting", label: "Waiting" },
  { value: "completed", label: "Done" },
];

interface StagesEditorProps {
  stages: WorkflowStage[];
  onChange: (next: WorkflowStage[]) => void;
  inventory: LabelInventoryItem[];
  problems: Record<string, string>;
  counts?: CountChange[];
  labelCounts?: Record<string, number>;
  extraActions?: ReactNode;
}

export function StagesEditor({
  stages,
  onChange,
  inventory,
  problems,
  counts,
  labelCounts,
  extraActions,
}: StagesEditorProps) {
  const [expandedNotes, setExpandedNotes] = useState<Record<number, boolean>>({});

  return (
    <div className="rule-compact-list">
      {stages.length === 0 && (
        <p className="settings-hint">With no stages, every issue shows as Backlog.</p>
      )}
      {stages.map((stage, i) => {
        const id = `settings-stage-${i}`;
        const nameProblem = problems[`workflow.stages.${i}.name`];
        const typeProblem = problems[`workflow.stages.${i}.type`];
        const count = stage.name.trim()
          ? counts?.find((c) => c.name?.toLowerCase() === stage.name.trim().toLowerCase())
          : undefined;
        const delta = count ? count.after - count.before : 0;
        const showDesc = stage.description.trim() !== "" || Boolean(expandedNotes[i]);

        return (
          <div key={i} className="rule-item">
            <div className="rule-item-head">
              <input
                id={`${id}-name`}
                type="text"
                className={`settings-input rule-name-input${nameProblem ? " error" : ""}`}
                aria-label={`Name of stage ${i + 1}`}
                aria-invalid={nameProblem ? true : undefined}
                placeholder="Stage name"
                value={stage.name}
                onChange={(e) => onChange(updateAt(stages, i, { name: e.target.value }))}
              />
              {count && (
                <span className={`rule-count-pill${delta !== 0 ? " changed" : ""}`}>
                  {delta !== 0 ? `${count.before}→${count.after}` : count.after}
                </span>
              )}
              <RowControls
                label={stage.name}
                index={i}
                count={stages.length}
                onMove={(deltaMove) => onChange(moveItem(stages, i, deltaMove))}
                onRemove={() => onChange(removeAt(stages, i))}
              />
            </div>

            {nameProblem && (
              <p className="settings-error-text" role="alert">
                {nameProblem}
              </p>
            )}

            <div className="rule-stage-meta">
              <div
                className="pulse-segmented compact"
                role="group"
                aria-label={`Kind of stage ${stage.name || i + 1}`}
              >
                {STAGE_KINDS.map((kind) => (
                  <button
                    key={kind.value}
                    type="button"
                    aria-pressed={stage.type === kind.value}
                    onClick={() => onChange(updateAt(stages, i, { type: kind.value }))}
                  >
                    {kind.label}
                  </button>
                ))}
              </div>
              {!showDesc && (
                <button
                  type="button"
                  className="rule-inline-link"
                  onClick={() => setExpandedNotes((prev) => ({ ...prev, [i]: true }))}
                >
                  + Description
                </button>
              )}
            </div>

            {typeProblem && (
              <p className="settings-error-text" role="alert">
                {typeProblem}
              </p>
            )}

            <MatcherInput
              id={`${id}-labels`}
              kind="label"
              value={stage.labels}
              inventory={inventory}
              matchCounts={labelCounts}
              ariaLabel={`Labels for stage ${stage.name || i + 1}`}
              problems={problemsWithPrefix(problems, `workflow.stages.${i}.labels`)}
              onChange={(labels) => onChange(updateAt(stages, i, { labels }))}
            />

            {showDesc && (
              <input
                id={`${id}-description`}
                type="text"
                className="settings-input rule-desc-input"
                aria-label={`Description for stage ${stage.name || i + 1}`}
                placeholder="Optional stage description…"
                value={stage.description}
                onChange={(e) => onChange(updateAt(stages, i, { description: e.target.value }))}
              />
            )}
          </div>
        );
      })}

      <div className="rule-list-footer">
        <div className="settings-add-row">
          <button
            type="button"
            className="pulse-btn-secondary settings-btn-small"
            onClick={() =>
              onChange([...stages, { name: "", labels: [], type: "active", description: "" }])
            }
          >
            <Plus size={13} />
            <span>Add stage</span>
          </button>
          {extraActions}
        </div>
      </div>
    </div>
  );
}
