import { useState } from "react";
import type { LabelInventoryItem } from "../../lib/labelInventory";
import { changedGroups, formatDelta, groupsForSection, type ImpactRow } from "../../lib/ruleImpact";
import type { ImpactSummary, SectionId } from "../../lib/types";
import type { RulePreview } from "./useRulePreview";

const VISIBLE_UNMAPPED = 8;
const WIDE_QUERY = "(min-width: 1200px)";

interface ImpactPanelProps {
  section: SectionId;
  canEdit: boolean;
  dirty: boolean;
  saving: boolean;
  hasClientProblems: boolean;
  preview: RulePreview;
  inventory: LabelInventoryItem[];
  rowNames: string[];
  onQuickAdd: (label: string, rowIndex: number) => void;
}

function plural(count: number, one: string, many: string): string {
  return `${count} ${count === 1 ? one : many}`;
}

function isWide(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(WIDE_QUERY).matches;
}

function ImpactRowItem({ row }: { row: ImpactRow }) {
  const changed = row.delta !== 0;
  return (
    <li className={`settings-impact-row${changed ? " changed" : ""}`}>
      <span className="settings-impact-label">{row.label}</span>
      {changed ? (
        <span className="settings-impact-count">
          {row.before} → {row.after}
          <span className="settings-impact-delta">{formatDelta(row.delta)}</span>
        </span>
      ) : (
        <span className="settings-impact-count">{row.after}</span>
      )}
    </li>
  );
}

interface UnmappedItemProps {
  name: string;
  count: number;
  color: string | null | undefined;
  rowNames: string[];
  showQuickAdd: boolean;
  disabled: boolean;
  onQuickAdd: (label: string, rowIndex: number) => void;
}

function UnmappedItem({
  name,
  count,
  color,
  rowNames,
  showQuickAdd,
  disabled,
  onQuickAdd,
}: UnmappedItemProps) {
  const [target, setTarget] = useState("");
  return (
    <li className="settings-impact-unmapped-row">
      <span className="settings-impact-label">
        <span
          className="settings-swatch"
          style={color ? { background: color } : undefined}
          aria-hidden="true"
        />
        <span className="settings-impact-name">{name}</span>
      </span>
      <span className="settings-impact-count">{count}</span>
      <span className="settings-impact-add">
        {showQuickAdd && rowNames.length > 0 && (
          <>
            <select
              className="settings-select"
              aria-label={`Add ${name} to…`}
              value={target}
              disabled={disabled}
              onChange={(e) => setTarget(e.target.value)}
            >
              <option value="">Add to…</option>
              {rowNames.map((rowName, i) => (
                <option key={i} value={i}>
                  {rowName || `Row ${i + 1}`}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="pulse-btn-secondary settings-btn-small"
              aria-label={`Add ${name} to the chosen row`}
              disabled={disabled || target === ""}
              onClick={() => {
                onQuickAdd(name, Number(target));
                setTarget("");
              }}
            >
              Add
            </button>
          </>
        )}
      </span>
    </li>
  );
}

interface UnmappedLabelsProps {
  impact: ImpactSummary;
  inventory: LabelInventoryItem[];
  showQuickAdd: boolean;
  disabled: boolean;
  rowNames: string[];
  onQuickAdd: (label: string, rowIndex: number) => void;
}

function UnmappedLabels({
  impact,
  inventory,
  showQuickAdd,
  disabled,
  rowNames,
  onQuickAdd,
}: UnmappedLabelsProps) {
  const [showAll, setShowAll] = useState(false);
  const [open, setOpen] = useState(isWide);
  if (impact.unmapped_label_total <= 0) return null;
  const labels = showAll ? impact.unmapped_labels : impact.unmapped_labels.slice(0, VISIBLE_UNMAPPED);
  const hidden = impact.unmapped_labels.length - VISIBLE_UNMAPPED;
  const more = impact.unmapped_label_total - impact.unmapped_labels.length;
  const byName = new Map(inventory.map((i) => [i.name, i]));

  return (
    <details
      className="settings-impact-group settings-impact-disclosure"
      open={open}
      onToggle={(e) => setOpen(e.currentTarget.open)}
    >
      <summary className="settings-impact-heading">
        Labels no rule uses ({impact.unmapped_label_total})
      </summary>
      <p className="settings-hint">
        These labels are on issues but none of your rules mention them.
      </p>
      <ul className="settings-impact-list settings-impact-unmapped">
        {labels.map((label) => (
          <UnmappedItem
            key={label.name}
            name={label.name}
            count={label.count}
            color={byName.get(label.name)?.color}
            rowNames={rowNames}
            showQuickAdd={showQuickAdd}
            disabled={disabled}
            onQuickAdd={onQuickAdd}
          />
        ))}
      </ul>
      {hidden > 0 && (
        <button
          type="button"
          className="pulse-btn-secondary settings-btn-small"
          aria-expanded={showAll}
          onClick={() => setShowAll((v) => !v)}
        >
          {showAll ? "Show fewer" : "Show all"}
        </button>
      )}
      {more > 0 && <p className="settings-hint">and {more} more</p>}
    </details>
  );
}

export function ImpactPanel({
  section,
  canEdit,
  dirty,
  saving,
  hasClientProblems,
  preview,
  inventory,
  rowNames,
  onQuickAdd,
}: ImpactPanelProps) {
  if (section === "colors") {
    return (
      <aside className="settings-impact" aria-label="Effect on your data">
        <h3 className="settings-impact-title">Effect on your data</h3>
        <div aria-live="polite" className="settings-impact-status">
          <p className="settings-hint">Colours do not change which issues are counted.</p>
        </div>
      </aside>
    );
  }
  const { status, error } = preview;
  const impact = canEdit && !hasClientProblems && status !== "error" ? preview.impact : null;
  const updating = status === "loading" || preview.pending;

  let statusText: string;
  if (!canEdit) {
    statusText = "Unlock editing to see how your changes affect the dashboard.";
  } else if (hasClientProblems || (status === "ready" && !preview.impact)) {
    statusText = "Fix the highlighted problems to see the effect.";
  } else if (status === "error") {
    statusText = error ?? "Could not calculate the effect.";
  } else if (!impact) {
    statusText = "Calculating…";
  } else if (impact.total_issues === 0) {
    statusText = "No collected issues fall under these rules yet.";
  } else {
    const projects = impact.project_ids.length;
    statusText =
      plural(impact.total_issues, "issue", "issues") +
      (projects > 0 ? ` in ${plural(projects, "project", "projects")}` : "");
  }
  const isTotal = Boolean(impact && impact.total_issues > 0);
  const overview = section === "projects" || section === "history" || section === "text";
  const groups = impact
    ? overview
      ? changedGroups(impact)
      : groupsForSection(section, impact)
    : [];
  const showError = canEdit && !hasClientProblems && status === "error";

  return (
    <aside className="settings-impact" aria-label="Effect on your data">
      <h3 className="settings-impact-title">Effect on your data</h3>
      <div aria-live="polite" className="settings-impact-status">
        <p className={isTotal ? "settings-impact-total" : showError ? "settings-error-text" : "settings-hint"}>
          {statusText}
          {impact && updating && <span className="settings-impact-updating"> Updating…</span>}
        </p>
      </div>
      {showError && (
        <button type="button" className="pulse-btn-secondary settings-btn-small" onClick={preview.retry}>
          Try again
        </button>
      )}
      {impact && impact.total_issues > 0 && (
        <>
          {overview && groups.length === 0 && (
            <p className="settings-hint">
              {dirty ? "Issue counts stay the same with these changes." : "No unsaved changes."}
            </p>
          )}
          {groups.map((group) => (
            <section key={group.title} className="settings-impact-group">
              <h4 className="settings-impact-heading">{group.title}</h4>
              <ul className="settings-impact-list">
                {group.rows.map((row) => (
                  <ImpactRowItem key={row.key} row={row} />
                ))}
              </ul>
            </section>
          ))}
          {!overview && (
          <UnmappedLabels
            impact={impact}
            inventory={inventory}
            showQuickAdd={section !== "quality"}
            disabled={saving}
            rowNames={rowNames}
            onQuickAdd={onQuickAdd}
          />
          )}
        </>
      )}
    </aside>
  );
}
