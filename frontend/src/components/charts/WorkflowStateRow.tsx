import { useMemo, useState } from "react";
import { buildStagePriorityBars } from "../../lib/analytics";
import type { IssueItem, ThemeMode } from "../../lib/types";
import { ChartTooltip, type TooltipState } from "./ChartTooltip";

interface WorkflowStateRowProps {
  issues: IssueItem[];
  stages: string[];
  palette: Record<string, string>;
  priorityOrder: string[];
  theme: ThemeMode;
  activeStage: string | null;
  activePriority: string | null;
  isStageChartFilterActive: boolean;
  onSelectBar: (stage: string, priority: string) => void;
}

export function WorkflowStateRow({
  issues,
  stages,
  palette,
  priorityOrder,
  theme,
  activeStage,
  activePriority,
  isStageChartFilterActive,
  onSelectBar,
}: WorkflowStateRowProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  const buckets = useMemo(
    () => buildStagePriorityBars(issues, stages, palette, priorityOrder, theme),
    [issues, stages, palette, priorityOrder, theme],
  );

  if (buckets.length === 0) {
    return (
      <div style={{ color: "var(--muted)", fontSize: "0.84rem", padding: "0.5rem 0" }}>
        No stage data available.
      </div>
    );
  }

  return (
    <div style={{ overflowX: "auto" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${buckets.length}, minmax(15rem, 1fr))`,
          gap: "0.65rem",
        }}
        aria-label="Issues by workflow state"
      >
        {buckets.map((bucket) => {
          const maxCount = Math.max(...bucket.bars.map((b) => b.count), 1);
          const stageMatches = activeStage === bucket.stage;
          const stageDimmed = isStageChartFilterActive && !stageMatches;

          return (
            <div
              key={bucket.stage}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "0.3rem",
                opacity: stageDimmed ? 0.25 : 1,
                transition: "opacity 0.16s ease",
              }}
            >
              <div
                style={{
                  textAlign: "center",
                  fontSize: "0.72rem",
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  color: stageMatches ? "var(--accent)" : "var(--muted)",
                  textTransform: "uppercase",
                }}
              >
                {bucket.stage}
              </div>

              {bucket.bars.length === 0 ? (
                <div
                  style={{
                    height: "92px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--muted)",
                    fontSize: "0.76rem",
                  }}
                >
                  No issues
                </div>
              ) : (
                <div
                  style={{
                    height: "92px",
                    display: "flex",
                    alignItems: "flex-end",
                    justifyContent: "center",
                    gap: "0.45rem",
                    paddingTop: "18px",
                  }}
                >
                  {bucket.bars.map((bar) => {
                    const barHeightPct = Math.max((bar.count / maxCount) * 100, 10);
                    const isSelected =
                      stageMatches &&
                      activePriority !== null &&
                      activePriority.toLowerCase() === bar.priority.toLowerCase();
                    const barDimmed =
                      stageMatches &&
                      activePriority !== null &&
                      activePriority.toLowerCase() !== bar.priority.toLowerCase();

                    return (
                      <button
                        key={bar.priority}
                        type="button"
                        aria-label={`${bucket.stage}, ${bar.priority}: ${bar.count} open issues`}
                        aria-pressed={isSelected}
                        onClick={() => onSelectBar(bucket.stage, bar.priority)}
                        onMouseEnter={(e) =>
                          setTooltip({
                            x: e.clientX,
                            y: e.clientY,
                            content: (
                              <div>
                                <strong>{bucket.stage}</strong> · {bar.priority}: {bar.count}
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
                          flex: "0 1 38px",
                          minWidth: "24px",
                          height: "100%",
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "center",
                          justifyContent: "flex-end",
                          gap: "3px",
                          border: "none",
                          background: "transparent",
                          padding: 0,
                          cursor: "pointer",
                          opacity: barDimmed ? 0.25 : 1,
                          transition: "opacity 0.16s ease",
                        }}
                      >
                        <span
                          style={{
                            fontFamily: "var(--font-mono)",
                            fontSize: "0.7rem",
                            fontWeight: 700,
                            color: "var(--heading)",
                            lineHeight: 1,
                          }}
                        >
                          {bar.count}
                        </span>
                        <div
                          style={{
                            width: "100%",
                            height: `${barHeightPct * 0.56}%`,
                            minHeight: "6px",
                            borderRadius: "5px 5px 2px 2px",
                            background: bar.color,
                            outline: isSelected ? "2px solid var(--heading)" : "none",
                          }}
                        />
                        <span
                          style={{
                            fontSize: "0.68rem",
                            color: "var(--muted)",
                            lineHeight: 1.1,
                          }}
                        >
                          {bar.priority}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <ChartTooltip tooltip={tooltip} />
    </div>
  );
}
