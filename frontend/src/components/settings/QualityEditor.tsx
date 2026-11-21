import { useMemo } from "react";
import type { LabelInventoryItem } from "../../lib/labelInventory";
import { getCategory, problemsWithPrefix } from "../../lib/ruleDraft";
import type { CountChange, RuleSetBody, ValidationConfig } from "../../lib/types";
import { MatcherInput } from "./MatcherInput";

const FIELD_OPTIONS: Array<[string, string]> = [
  ["assignee", "Assignee"],
  ["milestone", "Milestone"],
  ["description", "Description"],
  ["impact", "Impact"],
  ["priority", "Priority"],
];

interface QualityEditorProps {
  rule: RuleSetBody;
  onChange: (next: ValidationConfig) => void;
  inventory: LabelInventoryItem[];
  problems: Record<string, string>;
  counts?: CountChange[];
  labelCounts?: Record<string, number>;
}

function withKey<T>(record: Record<string, T[]>, key: string, list: T[]): Record<string, T[]> {
  const next = { ...record };
  if (list.length > 0) next[key] = list;
  else delete next[key];
  return next;
}

export function QualityEditor({
  rule,
  onChange,
  inventory,
  problems,
  counts,
  labelCounts,
}: QualityEditorProps) {
  const validation = rule.validation;

  const typeNames = useMemo(() => {
    const names = getCategory(rule, "type")
      .map((t) => t.name)
      .filter((n) => n.trim() !== "");
    const extra = [
      ...Object.keys(validation.required_labels),
      ...Object.keys(validation.required_fields),
    ].filter((n) => !names.includes(n));
    return [...names, ...new Set(extra)];
  }, [rule, validation.required_labels, validation.required_fields]);

  const staleProblem = problems["validation.stale_threshold_days"];
  const cycleProblem = problems["validation.max_cycle_time_days"];
  const staleCount = counts?.find((c) => c.name === "STALE");
  const cycleCount = counts?.find((c) => c.name === "EXCEEDS_CYCLE_TIME");

  const renderBadge = (c?: CountChange) => {
    if (!c) return null;
    const delta = c.after - c.before;
    return (
      <span className={`rule-count-pill${delta !== 0 ? " changed" : ""}`}>
        {delta !== 0 ? `${c.before}→${c.after}` : c.after}
      </span>
    );
  };

  return (
    <div className="rule-compact-list">
      <div className="rule-item rule-thresholds">
        <div className="rule-threshold-row">
          <label htmlFor="settings-stale-days">Stale after</label>
          <input
            id="settings-stale-days"
            type="number"
            min={1}
            step={1}
            className={`settings-input rule-num-input${staleProblem ? " error" : ""}`}
            value={Number.isNaN(validation.stale_threshold_days) ? "" : validation.stale_threshold_days}
            aria-invalid={staleProblem ? true : undefined}
            onChange={(e) =>
              onChange({
                ...validation,
                stale_threshold_days: e.target.value === "" ? Number.NaN : Number(e.target.value),
              })
            }
          />
          <span className="settings-hint">days quiet</span>
          {renderBadge(staleCount)}
        </div>
        {staleProblem && (
          <p className="settings-error-text" role="alert">
            {staleProblem}
          </p>
        )}

        <div className="rule-threshold-row">
          <label htmlFor="settings-cycle-days">Cycle time &gt;</label>
          <input
            id="settings-cycle-days"
            type="number"
            min={1}
            step={1}
            className={`settings-input rule-num-input${cycleProblem ? " error" : ""}`}
            value={Number.isNaN(validation.max_cycle_time_days) ? "" : validation.max_cycle_time_days}
            aria-invalid={cycleProblem ? true : undefined}
            onChange={(e) =>
              onChange({
                ...validation,
                max_cycle_time_days: e.target.value === "" ? Number.NaN : Number(e.target.value),
              })
            }
          />
          <span className="settings-hint">days</span>
          {renderBadge(cycleCount)}
        </div>
        {cycleProblem && (
          <p className="settings-error-text" role="alert">
            {cycleProblem}
          </p>
        )}
      </div>

      {typeNames.length === 0 && (
        <p className="settings-hint">Add an issue type first to set per-type requirements.</p>
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
          <div key={type} className="rule-item">
            <div className="rule-item-head">
              <strong className="rule-type-heading">{type}</strong>
            </div>
            <div className="rule-field-pills" role="group" aria-label={`Required fields for ${type}`}>
              {[...FIELD_OPTIONS, ...extraFields.map((f): [string, string] => [f, f])].map(
                ([value, label]) => {
                  const active = fields.includes(value);
                  return (
                    <button
                      key={value}
                      type="button"
                      className={`rule-field-pill${active ? " active" : ""}`}
                      aria-pressed={active}
                      onClick={() => toggle(value, !active)}
                    >
                      {label}
                    </button>
                  );
                },
              )}
            </div>
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
        );
      })}
    </div>
  );
}
