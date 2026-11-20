import { X } from "lucide-react";
import type { RuleSetBody, RuleSetItem } from "../../lib/types";

function scopeText(rule: RuleSetBody): string {
  const count = rule.project_ids.length;
  if (count === 0) return "Applies to all projects";
  return `Applies to ${count} ${count === 1 ? "project" : "projects"}`;
}

interface SettingsHeaderProps {
  selected: RuleSetItem | null;
  ruleSets: RuleSetItem[];
  onSelectRuleSet: (name: string) => void;
  onClose: () => void;
}

export function SettingsHeader({
  selected,
  ruleSets,
  onSelectRuleSet,
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
                onChange={(e) => onSelectRuleSet(e.target.value)}
              >
                {ruleSets.map((r) => (
                  <option key={r.name} value={r.name}>
                    {r.name}
                  </option>
                ))}
              </select>
            </>
          )}
          <span className="settings-meta-text">
            Team: {selected.rule.team || "Not set"} · {scopeText(selected.rule)}
          </span>
        </div>
      )}
      <button type="button" className="pulse-icon-btn" aria-label="Close settings" onClick={onClose}>
        <X size={15} />
      </button>
    </header>
  );
}
