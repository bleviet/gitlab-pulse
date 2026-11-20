import { Plus } from "lucide-react";
import type { LabelInventoryItem } from "../../lib/labelInventory";
import { moveItem, problemsWithPrefix, removeAt, STAGE_TYPES, updateAt } from "../../lib/ruleDraft";
import type { WorkflowStage } from "../../lib/types";
import { MatcherInput } from "./MatcherInput";
import { RowControls } from "./RowControls";
import { TextField } from "./TextField";

const STAGE_KINDS: Array<{ value: (typeof STAGE_TYPES)[number]; label: string; help: string }> = [
  { value: "active", label: "Active", help: "Being worked on." },
  { value: "waiting", label: "Waiting", help: "Queued for someone, e.g. review or testing." },
  { value: "completed", label: "Completed", help: "Finished." },
];

interface StagesEditorProps {
  stages: WorkflowStage[];
  onChange: (next: WorkflowStage[]) => void;
  inventory: LabelInventoryItem[];
  problems: Record<string, string>;
}

export function StagesEditor({ stages, onChange, inventory, problems }: StagesEditorProps) {
  return (
    <div className="settings-rows">
      {stages.length === 0 && (
        <p className="settings-hint">No stages yet. Every open issue will show as Backlog.</p>
      )}
      {stages.map((stage, i) => {
        const id = `settings-stage-${i}`;
        const typeProblem = problems[`workflow.stages.${i}.type`];
        const typeProblemId = `${id}-type-problem`;
        const selected = STAGE_KINDS.find((k) => k.value === stage.type);
        return (
          <div key={i} className="settings-row">
            <div className="settings-row-head">
              <span className="settings-row-index" aria-hidden="true">
                {i + 1}
              </span>
              <TextField
                id={`${id}-name`}
                label={`Name of stage ${i + 1}`}
                value={stage.name}
                problem={problems[`workflow.stages.${i}.name`]}
                onChange={(name) => onChange(updateAt(stages, i, { name }))}
              />
              <RowControls
                label={stage.name}
                index={i}
                count={stages.length}
                onMove={(delta) => onChange(moveItem(stages, i, delta))}
                onRemove={() => onChange(removeAt(stages, i))}
              />
            </div>

            <div className="settings-field">
              <span className="settings-field-label" id={`${id}-kind-label`}>
                What kind of stage is this?
              </span>
              <div
                className="pulse-segmented"
                role="group"
                aria-labelledby={`${id}-kind-label`}
                aria-describedby={typeProblem ? typeProblemId : undefined}
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
              <p className="settings-hint">
                {selected
                  ? `${selected.label}: ${selected.help}`
                  : "Active: being worked on. Waiting: queued for someone, e.g. review or testing. Completed: finished."}
              </p>
              {typeProblem && (
                <p id={typeProblemId} className="settings-error-text" role="alert">
                  {typeProblem}
                </p>
              )}
            </div>

            <div className="settings-field">
              <span className="settings-field-label">Issue is in this stage when it has this label</span>
              <MatcherInput
                id={`${id}-labels`}
                kind="label"
                value={stage.labels}
                inventory={inventory}
                ariaLabel={`Labels for stage ${stage.name || i + 1}`}
                problems={problemsWithPrefix(problems, `workflow.stages.${i}.labels`)}
                onChange={(labels) => onChange(updateAt(stages, i, { labels }))}
              />
            </div>

            <TextField
              id={`${id}-description`}
              label="Description (optional)"
              value={stage.description}
              onChange={(description) => onChange(updateAt(stages, i, { description }))}
            />
          </div>
        );
      })}
      <button
        type="button"
        className="pulse-btn-secondary settings-add-btn"
        onClick={() =>
          onChange([...stages, { name: "", labels: [], type: "active", description: "" }])
        }
      >
        <Plus size={14} />
        <span>Add stage</span>
      </button>
    </div>
  );
}
