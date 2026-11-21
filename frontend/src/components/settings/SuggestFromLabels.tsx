import { useMemo, useState } from "react";
import { Wand2 } from "lucide-react";
import type { LabelInventoryItem } from "../../lib/labelInventory";
import {
  applySuggestions,
  SUGGEST_SCOPES,
  suggestRows,
  type StageKind,
  type SuggestSection,
} from "../../lib/ruleSuggestions";
import type { RuleSetBody } from "../../lib/types";
import { rowNamesForSection } from "./sections";

const KIND_WORDS: Record<StageKind, string> = {
  active: "active stage",
  waiting: "waiting stage",
  completed: "completed stage",
};

const NOUNS: Record<SuggestSection, string> = {
  type: "issue types",
  impact: "impact levels",
  priority: "priority levels",
  stages: "stages",
};

interface SuggestFromLabelsProps {
  section: SuggestSection;
  rule: RuleSetBody;
  inventory: LabelInventoryItem[];
  canEdit: boolean;
  onChange: (next: RuleSetBody) => void;
}

export function SuggestFromLabels({
  section,
  rule,
  inventory,
  canEdit,
  onChange,
}: SuggestFromLabelsProps) {
  const [open, setOpen] = useState(false);
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const suggestions = useMemo(() => suggestRows(section, rule, inventory), [section, rule, inventory]);
  if (!canEdit) return null;

  const scope = SUGGEST_SCOPES[section][0];
  const empty = rowNamesForSection(rule, section).length === 0;
  if (!empty && suggestions.length === 0 && !open) return null;

  const openPanel = () => {
    setChosen(new Set(suggestions.map((s) => s.label)));
    setOpen(true);
  };

  const apply = () => {
    onChange(
      applySuggestions(
        section,
        rule,
        suggestions.filter((s) => chosen.has(s.label)),
      ),
    );
    setOpen(false);
  };

  return (
    <>
      {empty && (
        <p className="settings-hint settings-add-row-note">
          You have no {NOUNS[section]} yet. Start from the labels your issues already use.
        </p>
      )}
      <button
        type="button"
        className={`${empty ? "pulse-btn-primary" : "pulse-btn-secondary"} settings-btn-small`}
        aria-expanded={open}
        onClick={() => (open ? setOpen(false) : openPanel())}
      >
        <Wand2 size={13} />
        <span>Suggest ({suggestions.length})</span>
      </button>
      {open && (
        <div className="settings-suggest" role="group" aria-label="Suggestions from your labels">
          {suggestions.length === 0 ? (
            <p className="settings-hint">
              No further labels of the form {scope}::… were found on your issues.
            </p>
          ) : (
            <>
              <p className="settings-hint">
                We looked for labels of the form {scope}::… Tick the ones you want; nothing is saved
                until you choose Save &amp; apply.
              </p>
              <ul className="settings-suggest-list">
                {suggestions.map((s) => (
                  <li key={s.label}>
                    <label className="settings-check">
                      <input
                        type="checkbox"
                        checked={chosen.has(s.label)}
                        onChange={(e) => {
                          const next = new Set(chosen);
                          if (e.target.checked) next.add(s.label);
                          else next.delete(s.label);
                          setChosen(next);
                        }}
                      />
                      <span>
                        <strong>{s.name}</strong> ← {s.label} · {s.count}{" "}
                        {s.count === 1 ? "issue" : "issues"}
                        {s.kind && ` · ${KIND_WORDS[s.kind]}`}
                        {s.existingRowIndex !== null && " · added to the existing row"}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            </>
          )}
          <div className="settings-modal-actions">
            <button type="button" className="pulse-btn-secondary" onClick={() => setOpen(false)}>
              Cancel
            </button>
            {suggestions.length > 0 && (
              <button
                type="button"
                className="pulse-btn-primary"
                disabled={chosen.size === 0}
                onClick={apply}
              >
                Add selected
              </button>
            )}
          </div>
        </div>
      )}
    </>
  );
}
