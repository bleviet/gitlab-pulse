import { useMemo } from "react";
import {
  colorGroups,
  parseColorPath,
  removeColorEntry,
  resetColor,
  setColor,
  type ColorTheme,
} from "../../lib/ruleColors";
import type { PaletteDefaults, RuleSetBody } from "../../lib/types";
import { ColorCell } from "./ColorCell";

const THEMES: ColorTheme[] = ["light", "dark"];

interface ColorsEditorProps {
  rule: RuleSetBody;
  defaults: PaletteDefaults;
  problems: Record<string, string>;
  isDefault: boolean;
  canGoToDefault: boolean;
  readOnly: boolean;
  switchLocked: boolean;
  onGoToDefault: () => void;
  onChange: (next: RuleSetBody) => void;
}

export function ColorsEditor({
  rule,
  defaults,
  problems,
  isDefault,
  canGoToDefault,
  readOnly,
  switchLocked,
  onGoToDefault,
  onChange,
}: ColorsEditorProps) {
  const groups = useMemo(() => colorGroups(defaults, rule), [defaults, rule]);

  const cellProblems: Record<string, string> = {};
  const elsewhere: Array<[string, string]> = [];
  const shown = new Set(
    isDefault ? groups.flatMap((g) => g.rows.map((r) => r.key)) : [],
  );
  for (const [path, message] of Object.entries(problems)) {
    if (!path.startsWith("colors")) continue;
    const target = parseColorPath(path);
    if (target.kind === "theme" && shown.has(target.key)) {
      cellProblems[`${target.group}:${target.key}`] ??= message;
    } else {
      elsewhere.push([path, message]);
    }
  }
  const update = (colors: RuleSetBody["colors"]) => onChange({ ...rule, colors });

  const problemList = elsewhere.length > 0 && (
    <div className="settings-notice error" role="alert">
      <strong>Some colour settings cannot be used:</strong>
      <ul className="settings-problem-list">
        {elsewhere.map(([path, message]) => (
          <li key={path}>
            {message}{" "}
            <button
              type="button"
              className="pulse-btn-secondary settings-btn-small"
              disabled={readOnly}
              onClick={() => update(removeColorEntry(rule.colors, path))}
            >
              Remove this setting
            </button>
          </li>
        ))}
      </ul>
    </div>
  );

  if (!isDefault) {
    return (
      <div className="settings-rows">
        {problemList}
        <div className="settings-row">
          <p className="settings-intro-text">
            Colours are shared by all teams. They are edited in the default rule set.
          </p>
          {canGoToDefault && (
            <button
              type="button"
              className="pulse-btn-secondary settings-add-btn"
              disabled={switchLocked}
              onClick={onGoToDefault}
            >
              Go to the default rule set
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="settings-rows">
      {problemList}
      {groups.map((group, g) => (
        <div key={group.title} className="settings-row">
          <table className="settings-color-table">
            <caption className="settings-color-caption">{group.title}</caption>
            <thead>
              <tr>
                <th scope="col">Name</th>
                <th scope="col">Light theme</th>
                <th scope="col">Dark theme</th>
              </tr>
            </thead>
            <tbody>
              {group.rows.map((row) => (
                <tr key={row.key}>
                  <th scope="row">{row.label}</th>
                  {THEMES.map((theme) => (
                    <td key={theme}>
                      <ColorCell
                        idBase={`settings-color-${g}-${row.key}-${theme}`}
                        theme={theme}
                        name={row.label}
                        colorKey={row.key}
                        hasDefault={row.hasDefault}
                        colors={rule.colors}
                        defaults={defaults}
                        problem={cellProblems[`${theme}:${row.key}`]}
                        onSet={(hex) => update(setColor(rule.colors, theme, row.key, hex))}
                        onReset={() => update(resetColor(rule.colors, theme, row.key))}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {group.hints.map((hint) => (
            <p key={hint} className="settings-hint">
              {hint}
            </p>
          ))}
        </div>
      ))}
    </div>
  );
}
