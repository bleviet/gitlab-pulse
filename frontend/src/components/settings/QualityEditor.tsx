import { useMemo } from "react";
import type { LabelInventoryItem } from "../../lib/labelInventory";
import { getCategory, problemsWithPrefix } from "../../lib/ruleDraft";
import type { RuleSetBody, ValidationConfig } from "../../lib/types";
import { MatcherInput } from "./MatcherInput";

const FIELD_OPTIONS: Array<[string, string]> = [
  ["assignee", "Assignee"],
  ["milestone", "Milestone"],
  ["description", "Description"],
  ["severity", "Severity"],
  ["priority", "Priority"],
];

interface QualityEditorProps {
  rule: RuleSetBody;
  onChange: (next: ValidationConfig) => void;
  inventory: LabelInventoryItem[];
  problems: Record<string, string>;
  labelCounts?: Record<string, number>;
}

function withKey<T>(record: Record<string, T[]>, key: string, list: T[]): Record<string, T[]> {
  const next = { ...record };
  if (list.length > 0) next[key] = list;
  else delete next[key];
  return next;
}

export function QualityEditor({ rule, onChange, inventory, problems, labelCounts }: QualityEditorProps) {
  const validation = rule.validation;

  const typeNames = useMemo(() => {
    const names = getCategory(rule, "type").map((t) => t.name).filter((n) => n.trim() !== "");
    const extra = [
      ...Object.keys(validation.required_labels),
      ...Object.keys(validation.required_fields),
    ].filter((n) => !names.includes(n));
    return [...names, ...new Set(extra)];
  }, [rule, validation.required_labels, validation.required_fields]);

  const staleProblem = problems["validation.stale_threshold_days"];
  const cycleProblem = problems["validation.max_cycle_time_days"];

  const numberField = (
    id: string,
    before: string,
    after: string,
    value: number,
    problem: string | undefined,
    onValue: (n: number) => void,
  ) => (
    <div className="settings-field">
      <div className="settings-sentence">
        <label htmlFor={id}>{before}</label>
        <input
          id={id}
          type="number"
          min={1}
          step={1}
          className={`settings-input settings-number${problem ? " error" : ""}`}
          value={Number.isNaN(value) ? "" : value}
          aria-invalid={problem ? true : undefined}
          aria-describedby={problem ? `${id}-problem` : undefined}
          onChange={(e) => onValue(e.target.value === "" ? Number.NaN : Number(e.target.value))}
        />
        <span>{after}</span>
      </div>
      {problem && (
        <p id={`${id}-problem`} className="settings-error-text" role="alert">
          {problem}
        </p>
      )}
    </div>
  );

  return (
    <div className="settings-rows">
      <div className="settings-row">
        {numberField(
          "settings-stale-days",
          "Mark an open issue as stale after",
          "days without an update",
          validation.stale_threshold_days,
          staleProblem,
          (n) => onChange({ ...validation, stale_threshold_days: n }),
        )}
        {numberField(
          "settings-cycle-days",
          "Flag issues whose cycle time exceeds",
          "days",
          validation.max_cycle_time_days,
          cycleProblem,
          (n) => onChange({ ...validation, max_cycle_time_days: n }),
        )}
      </div>

      <h3 className="settings-subtitle">Required per issue type</h3>
      <p className="settings-hint">
        For each issue type, choose labels it must carry and fields it must have filled in.
        Issues that miss them are flagged on the dashboard.
      </p>
      {typeNames.length === 0 && (
        <p className="settings-hint">Add an issue type first to set requirements for it.</p>
      )}
      {typeNames.map((type, t) => {
        const id = `settings-quality-${t}`;
        const fields = validation.required_fields[type] ?? [];
        const known = new Set(FIELD_OPTIONS.map(([value]) => value));
        const extraFields = fields.filter((f) => !known.has(f));
        const toggle = (value: string, checked: boolean) => {
          const next = checked ? [...fields, value] : fields.filter((f) => f !== value);
          onChange({
            ...validation,
            required_fields: withKey(validation.required_fields, type, next),
          });
        };
        return (
          <div key={type} className="settings-row">
            <h4 className="settings-row-title">{type}</h4>
            <div className="settings-field">
              <span className="settings-field-label">Required labels</span>
              <MatcherInput
                id={`${id}-labels`}
                kind="label"
                value={validation.required_labels[type] ?? []}
                inventory={inventory}
                matchCounts={labelCounts}
                ariaLabel={`Required labels for ${type}`}
                problems={problemsWithPrefix(problems, `validation.required_labels.${type}`)}
                onChange={(next) =>
                  onChange({
                    ...validation,
                    required_labels: withKey(validation.required_labels, type, next),
                  })
                }
              />
            </div>
            <fieldset className="settings-fields-group">
              <legend className="settings-field-label">Required fields</legend>
              {[...FIELD_OPTIONS, ...extraFields.map((f): [string, string] => [f, f])].map(
                ([value, label]) => (
                  <label key={value} className="settings-check">
                    <input
                      type="checkbox"
                      checked={fields.includes(value)}
                      onChange={(e) => toggle(value, e.target.checked)}
                    />
                    <span>{label}</span>
                  </label>
                ),
              )}
            </fieldset>
          </div>
        );
      })}
    </div>
  );
}
