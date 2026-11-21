import { useState, type ReactNode } from "react";
import { Plus } from "lucide-react";
import type { LabelInventoryItem } from "../../lib/labelInventory";
import { resetColor, setColor, type ColorMap, type ColorTheme } from "../../lib/ruleColors";
import { moveItem, problemsWithPrefix, removeAt, updateAt } from "../../lib/ruleDraft";
import { formatDelta } from "../../lib/ruleImpact";
import type { CountChange, MatcherRule, PaletteDefaults } from "../../lib/types";
import { InlineColorDot } from "./InlineColorDot";
import { MatcherInput } from "./MatcherInput";
import { RowControls } from "./RowControls";

export type ClassificationCategoryId = "type" | "impact" | "priority";

const COPY: Record<ClassificationCategoryId, { noun: string; add: string; empty: string }> = {
  type: {
    noun: "issue type",
    add: "Add type",
    empty: "No issue types yet.",
  },
  impact: {
    noun: "impact",
    add: "Add impact",
    empty: "No impact levels yet.",
  },
  priority: {
    noun: "priority",
    add: "Add priority",
    empty: "No priority levels yet.",
  },
};

function findCount(counts: CountChange[] | undefined, name: string): CountChange | undefined {
  if (!counts || !name.trim()) return undefined;
  const target = name.trim().toLowerCase();
  return counts.find((c) => c.name?.toLowerCase() === target);
}

interface ClassificationEditorProps {
  category: ClassificationCategoryId;
  rows: MatcherRule[];
  onChange: (next: MatcherRule[]) => void;
  inventory: LabelInventoryItem[];
  problems: Record<string, string>;
  counts?: CountChange[];
  labelCounts?: Record<string, number>;
  titleCounts?: Record<string, number>;
  colors?: ColorMap;
  paletteDefaults?: PaletteDefaults;
  theme?: ColorTheme;
  canEditColors?: boolean;
  onChangeColors?: (next: ColorMap) => void;
  extraActions?: ReactNode;
}

export function ClassificationEditor({
  category,
  rows,
  onChange,
  inventory,
  problems,
  counts,
  labelCounts,
  titleCounts,
  colors,
  paletteDefaults,
  theme = "dark",
  canEditColors = false,
  onChangeColors,
  extraActions,
}: ClassificationEditorProps) {
  const [expandedTitles, setExpandedTitles] = useState<Record<number, boolean>>({});
  const copy = COPY[category];
  const base = `classification.${category}`;
  const unsetCount = counts?.find((c) => c.name === null);

  return (
    <div className="rule-compact-list">
      {rows.length === 0 && <p className="settings-hint">{copy.empty}</p>}
      {rows.map((row, i) => {
        const id = `settings-${category}-${i}`;
        const nameProblem = problems[`${base}.${i}.name`];
        const count = findCount(counts, row.name);
        const delta = count ? count.after - count.before : 0;
        const showTitle =
          category === "type" && (row.title.length > 0 || Boolean(expandedTitles[i]));

        return (
          <div key={i} className="rule-item">
            <div className="rule-item-head">
              {colors && paletteDefaults && onChangeColors && (
                <InlineColorDot
                  name={row.name}
                  colorKey={row.name}
                  colors={colors}
                  defaults={paletteDefaults}
                  theme={theme}
                  canEdit={canEditColors}
                  onSet={(hex) => onChangeColors(setColor(colors, theme, row.name, hex))}
                  onReset={() => onChangeColors(resetColor(colors, theme, row.name))}
                />
              )}
              <input
                id={`${id}-name`}
                type="text"
                className={`settings-input rule-name-input${nameProblem ? " error" : ""}`}
                aria-label={`Name of ${copy.noun} ${i + 1}`}
                aria-invalid={nameProblem ? true : undefined}
                placeholder={`Name (${copy.noun})`}
                value={row.name}
                onChange={(e) => onChange(updateAt(rows, i, { name: e.target.value }))}
              />
              {count && (
                <span
                  className={`rule-count-pill${delta !== 0 ? " changed" : ""}`}
                  title={
                    delta !== 0
                      ? `${count.before} issues before, ${count.after} after`
                      : `${count.after} matching issues`
                  }
                >
                  {delta !== 0 ? `${count.before}→${count.after}` : count.after}
                </span>
              )}
              <RowControls
                label={row.name}
                index={i}
                count={rows.length}
                onMove={(deltaMove) => onChange(moveItem(rows, i, deltaMove))}
                onRemove={() => onChange(removeAt(rows, i))}
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
              ariaLabel={`Labels for ${row.name || `${copy.noun} ${i + 1}`}`}
              problems={problemsWithPrefix(problems, `${base}.${i}.labels`)}
              onChange={(labels) => onChange(updateAt(rows, i, { labels }))}
            />

            {category === "type" &&
              (showTitle ? (
                <div className="rule-sub-field">
                  <span className="rule-sub-label">Title words</span>
                  <MatcherInput
                    id={`${id}-title`}
                    kind="title"
                    value={row.title}
                    inventory={inventory}
                    matchCounts={titleCounts}
                    ariaLabel={`Title words for ${row.name || `${copy.noun} ${i + 1}`}`}
                    problems={problemsWithPrefix(problems, `${base}.${i}.title`)}
                    onChange={(title) => onChange(updateAt(rows, i, { title }))}
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
              ))}
          </div>
        );
      })}

      <div className="rule-list-footer">
        <div className="settings-add-row">
          <button
            type="button"
            className="pulse-btn-secondary settings-btn-small"
            onClick={() => onChange([...rows, { name: "", labels: [], title: [] }])}
          >
            <Plus size={13} />
            <span>{copy.add}</span>
          </button>
          {extraActions}
        </div>
        {unsetCount && (unsetCount.after > 0 || unsetCount.before !== unsetCount.after) && (
          <span className="rule-unset-meta">
            Unset:{" "}
            {unsetCount.before !== unsetCount.after
              ? `${unsetCount.before}→${unsetCount.after} (${formatDelta(unsetCount.after - unsetCount.before)})`
              : unsetCount.after}
          </span>
        )}
      </div>
    </div>
  );
}
