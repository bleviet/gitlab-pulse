import { Plus, X } from "lucide-react";
import type { RuleSetItem } from "../../lib/types";

function scopeText(item: RuleSetItem, isDefault: boolean, ruleSetCount: number): string {
  const count = item.rule.project_ids.length;
  if (isDefault) {
    return ruleSetCount > 1 ? "Applies to all other projects" : "Applies to all projects";
  }
  if (count === 0) return "Applies to no projects";
  return `Applies to ${count} ${count === 1 ? "project" : "projects"}`;
}

function optionText(item: RuleSetItem, isDefault: boolean): string {
  const count = item.rule.project_ids.length;
  const team = item.rule.team || item.name;
  if (isDefault) return `${team} — all other projects`;
  if (count === 0) return `${team} — no projects`;
  return `${team} — ${count} ${count === 1 ? "project" : "projects"}`;
}

interface SettingsHeaderProps {
  selected: RuleSetItem | null;
  ruleSets: RuleSetItem[];
  canEdit: boolean;
  defaultName: string | null;
  newBlocked: boolean;
  saving: boolean;
  onSelectRuleSet: (name: string) => void;
  onNewRuleSet: () => void;
  onClose: () => void;
}

export function SettingsHeader({
  selected,
  ruleSets,
  canEdit,
  defaultName,
  newBlocked,
  saving,
  onSelectRuleSet,
  onNewRuleSet,
  onClose,
}: SettingsHeaderProps) {
  return (
    <header className="settings-header">
      <h2 id="settings-title" className="settings-title">
        Settings
      </h2>
      {selected && (
        <div className="settings-header-meta">
          {ruleSets.length > 1 && (
            <>
              <label htmlFor="settings-rule-set" className="settings-visually-hidden">
                Rule set
              </label>
              <select
                id="settings-rule-set"
                className="settings-select"
                value={selected.name}
                disabled={saving}
                onChange={(e) => onSelectRuleSet(e.target.value)}
              >
                {ruleSets.map((r) => (
                  <option key={r.name} value={r.name}>
                    {optionText(r, r.name === defaultName)}
                  </option>
                ))}
              </select>
            </>
          )}
          <span className="settings-meta-text">
            Team: {selected.rule.team || "Not set"} · {scopeText(selected, selected.name === defaultName, ruleSets.length)}
          </span>
        </div>
      )}
      {canEdit && selected && (
        <>
          {newBlocked && (
            <span id="settings-new-hint" className="settings-hint">
              Save or discard your changes first.
            </span>
          )}
          <button
            type="button"
            className="pulse-btn-secondary"
            disabled={newBlocked}
            aria-describedby={newBlocked ? "settings-new-hint" : undefined}
            onClick={onNewRuleSet}
          >
            <Plus size={14} />
            <span>New rule set</span>
          </button>
        </>
      )}
      <button type="button" className="pulse-icon-btn" aria-label="Close settings" onClick={onClose}>
        <X size={15} />
      </button>
    </header>
  );
}
