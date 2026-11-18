import { useMemo, useState } from "react";
import { buildQualitySignalsData } from "../../lib/analytics";
import type { IssueItem } from "../../lib/types";
import { ChartTooltip, type TooltipState } from "./ChartTooltip";

interface QualitySignalsChartProps {
  issues: IssueItem[];
  palette: Record<string, string>;
  activeSignal: string | null;
  onSelectSignal: (signalCode: string) => void;
}

export function QualitySignalsChart({
  issues,
  palette,
  activeSignal,
  onSelectSignal,
}: QualitySignalsChartProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const bars = useMemo(() => buildQualitySignalsData(issues, palette), [issues, palette]);

  if (bars.length === 0) {
    return (
      <div
        style={{
          height: "152px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--muted)",
          fontSize: "0.82rem",
        }}
      >
        No quality signals available
      </div>
    );
  }

  const maxCount = Math.max(...bars.map((b) => b.count), 1);

  return (
    <div
      style={{
        height: "152px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        gap: "0.65rem",
      }}
      aria-label="Issue quality signals bar chart"
    >
      {bars.map((bar) => {
        const pct = Math.max((bar.count / maxCount) * 100, 3);
        const isSelected = activeSignal === bar.code;
        const isDimmed = activeSignal !== null && activeSignal !== bar.code;
        return (
          <button
            key={bar.code}
            type="button"
            aria-pressed={isSelected}
            onClick={() => onSelectSignal(bar.code)}
            onMouseEnter={(e) =>
              setTooltip({
                x: e.clientX,
                y: e.clientY,
                content: (
                  <div>
                    <strong>{bar.label}</strong>: {bar.count} open issues
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
              gridTemplateColumns: "110px 1fr 40px",
              alignItems: "center",
              gap: "0.55rem",
              border: "none",
              background: "transparent",
              padding: "2px 0",
              cursor: "pointer",
              textAlign: "left",
              opacity: isDimmed ? 0.3 : 1,
              transition: "opacity 0.16s ease",
            }}
          >
            <span
              style={{
                fontSize: "0.78rem",
                color: isSelected ? "var(--heading)" : "var(--text)",
                fontWeight: isSelected ? 700 : 500,
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {bar.label}
            </span>
            <div
              style={{
                height: "14px",
                borderRadius: "6px",
                background: "var(--chart-grid)",
                overflow: "hidden",
                outline: isSelected ? `1.5px solid ${bar.color}` : "none",
              }}
            >
              <div
                style={{
                  width: `${pct}%`,
                  height: "100%",
                  borderRadius: "6px",
                  background: bar.color,
                  transition: "width 0.25s var(--ease)",
                }}
              />
            </div>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.78rem",
                fontWeight: 700,
                color: "var(--heading)",
                textAlign: "right",
              }}
            >
              {bar.count}
            </span>
          </button>
        );
      })}
      <ChartTooltip tooltip={tooltip} />
    </div>
  );
}
