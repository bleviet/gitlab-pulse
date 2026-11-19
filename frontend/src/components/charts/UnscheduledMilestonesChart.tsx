import { useState, type ReactNode } from "react";
import { formatShare } from "../../lib/analytics";
import {
  selectVisibleUnscheduledRows,
  type UnscheduledModel,
  type UnscheduledSegment,
} from "../../lib/timeline";
import type { ValueMode } from "../../lib/types";
import { ChartTooltip, type TooltipState } from "./ChartTooltip";

const MAX_ROWS = 6;

export type UnscheduledMode = "total" | "priority" | "type";

interface UnscheduledMilestonesChartProps {
  model: UnscheduledModel;
  mode: UnscheduledMode;
  valueMode: ValueMode;
  palette: Record<string, string>;
  activeMilestone: string | null;
  maxRows: number;
  onSelectMilestone: (title: string) => void;
}

export function UnscheduledMilestonesChart({
  model,
  mode,
  valueMode,
  palette,
  activeMilestone,
  maxRows,
  onSelectMilestone,
}: UnscheduledMilestonesChartProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const ringColor = palette.ms_unscheduled ?? palette.neutral ?? "#7a8fa8";
  const visibleRows = selectVisibleUnscheduledRows(model.rows, activeMilestone, maxRows);
  const moreCount = model.rows.length - visibleRows.length;
  const maxOpen = Math.max(...model.rows.map((r) => r.openCount), 1);
  const legend =
    mode === "priority" ? model.priorityLegend : mode === "type" ? model.typeLegend : [];

  const renderBreakdown = (segments: UnscheduledSegment[], rowOpen: number) =>
    segments.map((seg) => (
      <div key={seg.label}>
        {seg.label} {seg.count} ({formatShare(seg.count, rowOpen)})
      </div>
    ));

  return (
    <div
      style={{ display: "flex", flexDirection: "column", gap: "0.42rem" }}
      aria-label="Unscheduled milestones bar chart"
    >
      {visibleRows.map((row) => {
        const isSelected = activeMilestone === row.title;
        const isDimmed = activeMilestone !== null && activeMilestone !== row.title;
        const segments =
          mode === "priority" ? row.byPriority : mode === "type" ? row.byType : null;
        return (
          <button
            key={row.title}
            type="button"
            aria-pressed={isSelected}
            onClick={() => onSelectMilestone(row.title)}
            onMouseEnter={(e) =>
              setTooltip({
                x: e.clientX,
                y: e.clientY,
                content: (
                  <div>
                    <strong>{row.title}</strong>
                    <div>No due date</div>
                    <div>
                      Open {row.openCount} of {row.totalCount} · oldest open {row.oldestOpenDays}d
                    </div>
                    {renderBreakdown(mode === "type" ? row.byType : row.byPriority, row.openCount)}
                  </div>
                ),
              })
            }
            onMouseMove={(e) =>
              setTooltip((prev) => (prev ? { ...prev, x: e.clientX, y: e.clientY } : null))
            }
            onMouseLeave={() => setTooltip(null)}
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(88px, 108px) 1fr 34px",
              alignItems: "center",
              gap: "0.45rem",
              border: "none",
              background: "transparent",
              padding: "1px 0",
              cursor: "pointer",
              textAlign: "left",
              opacity: isDimmed ? 0.3 : 1,
              transition: "opacity 0.16s ease",
            }}
          >
            <span
              style={{
                display: "flex",
                alignItems: "center",
                gap: "0.35rem",
                minWidth: 0,
                fontSize: "0.75rem",
                color: isSelected ? "var(--heading)" : "var(--text)",
                fontWeight: isSelected ? 700 : 500,
              }}
            >
              <span
                aria-hidden="true"
                style={{
                  width: 9,
                  height: 9,
                  flexShrink: 0,
                  boxSizing: "border-box",
                  borderRadius: "50%",
                  border: `1.5px dashed ${ringColor}`,
                }}
              />
              <span
                style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
              >
                {row.title}
              </span>
            </span>
            <div
              style={{
                display: "flex",
                height: "11px",
                borderRadius: "5px",
                background: "var(--chart-grid)",
                overflow: "hidden",
                outline: isSelected ? `1.5px solid ${ringColor}` : "none",
              }}
            >
              {segments === null ? (
                <div
                  style={{
                    width: `${Math.max((row.openCount / maxOpen) * 100, 3)}%`,
                    height: "100%",
                    borderRadius: "5px",
                    background: ringColor,
                    transition: "width 0.25s var(--ease)",
                  }}
                />
              ) : (
                segments.map((seg) => (
                  <div
                    key={seg.label}
                    style={{
                      width: `${(seg.count / maxOpen) * 100}%`,
                      height: "100%",
                      background: seg.color,
                      transition: "width 0.25s var(--ease)",
                    }}
                  />
                ))
              )}
            </div>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.74rem",
                fontWeight: 700,
                color: "var(--heading)",
                textAlign: "right",
              }}
            >
              {valueMode === "percent"
                ? formatShare(row.openCount, model.openIssueCount)
                : row.openCount}
            </span>
          </button>
        );
      })}
      {moreCount > 0 && (
        <div style={{ fontSize: "0.72rem", color: "var(--muted)" }}>
          +{moreCount} more without a due date
        </div>
      )}
      {legend.length > 0 && (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            alignItems: "center",
            gap: "0.2rem 0.65rem",
            fontSize: "0.72rem",
            color: "var(--muted)",
          }}
        >
          {legend.map((seg) => (
            <span
              key={seg.label}
              style={{ display: "inline-flex", alignItems: "center", gap: "0.28rem" }}
            >
              <span
                style={{ width: 8, height: 8, borderRadius: 999, background: seg.color }}
              />
              {seg.label}
              {valueMode === "percent"
                ? ` ${formatShare(seg.count, model.openIssueCount)}`
                : ""}
            </span>
          ))}
        </div>
      )}
      {model.hiddenClosedCount > 0 && (
        <div
          style={{
            borderTop: "1px solid var(--line)",
            paddingTop: "0.35rem",
            fontSize: "0.72rem",
            color: "var(--muted)",
          }}
        >
          {model.hiddenClosedCount}{" "}
          {model.hiddenClosedCount === 1 ? "milestone" : "milestones"} without a due date and all
          issues closed {model.hiddenClosedCount === 1 ? "is" : "are"} hidden.
        </div>
      )}
      <ChartTooltip tooltip={tooltip} />
    </div>
  );
}

interface UnscheduledMilestonesPanelBodyProps {
  model: UnscheduledModel;
  mode: UnscheduledMode;
  valueMode: ValueMode;
  palette: Record<string, string>;
  activeMilestone: string | null;
  onChangeMode: (mode: UnscheduledMode) => void;
  onSelectMilestone: (title: string) => void;
  headExtra?: ReactNode;
}

const MODE_LABELS: Array<[UnscheduledMode, string]> = [
  ["total", "Total"],
  ["priority", "Priority"],
  ["type", "Type"],
];

export function UnscheduledMilestonesPanelBody({
  model,
  mode,
  valueMode,
  palette,
  activeMilestone,
  onChangeMode,
  onSelectMilestone,
  headExtra,
}: UnscheduledMilestonesPanelBodyProps) {
  return (
    <>
      <div className="pulse-panel-head unscheduled-head">
        <span className="pulse-panel-title">Unscheduled Milestones</span>
        <div className="unscheduled-head-controls">
          <div className="pulse-segmented compact" role="group" aria-label="Bar breakdown">
            {MODE_LABELS.map(([m, label]) => (
              <button
                key={m}
                type="button"
                aria-pressed={mode === m}
                onClick={() => onChangeMode(m)}
              >
                {label}
              </button>
            ))}
          </div>
          {headExtra}
        </div>
      </div>
      <UnscheduledMilestonesChart
        model={model}
        mode={mode}
        valueMode={valueMode}
        palette={palette}
        activeMilestone={activeMilestone}
        maxRows={MAX_ROWS}
        onSelectMilestone={onSelectMilestone}
      />
    </>
  );
}
