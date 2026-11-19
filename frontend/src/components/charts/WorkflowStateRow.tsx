import { useEffect, useMemo, useRef, useState } from "react";
import { buildStagePriorityBars, formatShare, type StageBarBucket } from "../../lib/analytics";
import { contrastTextForHex } from "../../lib/colors";
import type { IssueItem, ThemeMode, ValueMode } from "../../lib/types";
import { ChartTooltip, type TooltipState } from "./ChartTooltip";

interface WorkflowStateRowProps {
  issues: IssueItem[];
  stages: string[];
  palette: Record<string, string>;
  priorityOrder: string[];
  theme: ThemeMode;
  valueMode: ValueMode;
  activeStage: string | null;
  activePriority: string | null;
  isStageChartFilterActive: boolean;
  onSelectBar: (
    stage: string,
    priority: string,
    filterState: "opened" | "closed" | "all",
  ) => void;
  onSelectStage?: (stage: string, filterState: "opened" | "closed" | "all") => void;
}

export function WorkflowStateRow({
  issues,
  stages,
  palette,
  priorityOrder,
  theme,
  valueMode,
  activeStage,
  activePriority,
  isStageChartFilterActive,
  onSelectBar,
  onSelectStage,
}: WorkflowStateRowProps) {
  const listRef = useRef<HTMLDivElement | null>(null);
  const [containerWidth, setContainerWidth] = useState(340);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    setContainerWidth(el.clientWidth || 340);
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 0) {
          setContainerWidth(Math.round(entry.contentRect.width));
        }
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const buckets = useMemo(
    () => buildStagePriorityBars(issues, stages, palette, priorityOrder, theme),
    [issues, stages, palette, priorityOrder, theme],
  );

  if (buckets.length === 0) {
    return (
      <div
        ref={listRef}
        style={{ color: "var(--muted)", fontSize: "0.78rem", padding: "0.4rem 0" }}
      >
        No stage data available.
      </div>
    );
  }

  const openBuckets = buckets.filter((b) => !b.isClosedOnly);
  const closedBuckets = buckets.filter((b) => b.isClosedOnly);
  const maxOpenTotal = Math.max(...openBuckets.map((b) => b.total), 1);
  const maxClosedTotal = Math.max(...closedBuckets.map((b) => b.total), 1);
  const openTotal = openBuckets.reduce((sum, b) => sum + b.total, 0);
  const closedTotal = closedBuckets.reduce((sum, b) => sum + b.total, 0);
  const trackPx = Math.max(containerWidth - 96 - 38 - 14, 80);

  const renderRow = (bucket: StageBarBucket, scaleMax: number, groupTotal: number) => {
    const stageMatches = activeStage === bucket.stage;
    const stageDimmed = isStageChartFilterActive && !stageMatches;

    return (
      <div
        key={bucket.stage}
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(84px, 96px) 1fr 38px",
          alignItems: "center",
          gap: "0.45rem",
          opacity: stageDimmed ? 0.24 : 1,
          transition: "opacity 0.16s ease",
        }}
      >
        <button
          type="button"
          title={`${bucket.stage} (${bucket.total})`}
          aria-pressed={stageMatches && activePriority === null}
          onClick={() => onSelectStage?.(bucket.stage, bucket.filterState)}
          style={{
            border: "none",
            background: "transparent",
            padding: 0,
            textAlign: "left",
            cursor: onSelectStage ? "pointer" : "default",
            fontSize: "0.74rem",
            fontWeight: stageMatches ? 700 : 500,
            color: stageMatches ? "var(--accent)" : bucket.isClosedOnly ? "var(--muted)" : "var(--text)",
            whiteSpace: "nowrap",
            overflow: "hidden",
            textOverflow: "ellipsis",
          }}
        >
          {bucket.stage}
        </button>

        <div
          style={{
            height: "18px",
            borderRadius: "5px",
            background: "var(--chart-grid)",
            display: "flex",
            alignItems: "stretch",
            gap: "1px",
            overflow: "hidden",
          }}
        >
          {bucket.bars.map((bar) => {
            const widthPct = Math.max((bar.count / scaleMax) * 100, 2);
            const segmentPx = (widthPct / 100) * trackPx;
            const countStr =
              valueMode === "percent" ? formatShare(bar.count, bucket.total) : String(bar.count);
            const showCount = segmentPx >= countStr.length * 6 + 8;
            const isSelected =
              stageMatches &&
              activePriority !== null &&
              activePriority.toLowerCase() === bar.priority.toLowerCase();
            const barDimmed =
              stageMatches &&
              activePriority !== null &&
              activePriority.toLowerCase() !== bar.priority.toLowerCase();
            const stateWord = bucket.isClosedOnly
              ? "closed "
              : bucket.filterState === "all"
                ? ""
                : "open ";

            return (
              <button
                key={bar.priority}
                type="button"
                aria-label={`${bucket.stage}, ${bar.priority}: ${bar.count} ${stateWord}issues`}
                aria-pressed={isSelected}
                onClick={() => onSelectBar(bucket.stage, bar.priority, bucket.filterState)}
                onMouseEnter={(e) =>
                  setTooltip({
                    x: e.clientX,
                    y: e.clientY,
                    content: (
                      <div>
                        <strong>{bucket.stage}</strong>
                        {bucket.isClosedOnly ? " (Closed)" : ""} · {bar.priority}: {bar.count} ({formatShare(bar.count, bucket.total)} of stage)
                      </div>
                    ),
                  })
                }
                onMouseMove={(e) =>
                  setTooltip((prev) =>
                    prev ? { ...prev, x: e.clientX, y: e.clientY } : null,
                  )
                }
                onMouseLeave={() => setTooltip(null)}
                style={{
                  width: `${widthPct}%`,
                  minWidth: "5px",
                  height: "100%",
                  border: "none",
                  padding: 0,
                  background: bar.color,
                  color: contrastTextForHex(bar.color),
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.62rem",
                  fontWeight: 700,
                  lineHeight: 1,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  overflow: "hidden",
                  whiteSpace: "nowrap",
                  cursor: "pointer",
                  opacity: barDimmed ? 0.24 : 1,
                  outline: isSelected ? "2px solid var(--heading)" : "none",
                  outlineOffset: "-2px",
                  transition: "opacity 0.16s ease",
                }}
              >
                {showCount ? countStr : null}
              </button>
            );
          })}
        </div>

        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.73rem",
            fontWeight: 700,
            color: bucket.isClosedOnly ? "var(--muted)" : "var(--heading)",
            textAlign: "right",
          }}
        >
          {valueMode === "percent" ? formatShare(bucket.total, groupTotal) : bucket.total}
        </span>
      </div>
    );
  };

  return (
    <div
      ref={listRef}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "0.34rem",
      }}
      aria-label="Issues by workflow state"
    >
      {openBuckets.map((bucket) => renderRow(bucket, maxOpenTotal, openTotal))}
      {openBuckets.length > 0 && closedBuckets.length > 0 && (
        <div
          aria-hidden="true"
          style={{ borderTop: "1px dashed var(--line-strong)", margin: "0.12rem 0" }}
        />
      )}
      {closedBuckets.map((bucket) => renderRow(bucket, maxClosedTotal, closedTotal))}
      <ChartTooltip tooltip={tooltip} />
    </div>
  );
}
