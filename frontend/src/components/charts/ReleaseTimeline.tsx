import { useEffect, useMemo, useRef, useState } from "react";
import { buildMilestoneTimelineData } from "../../lib/timeline";
import type { IssueItem } from "../../lib/types";
import { ChartTooltip, type TooltipState } from "./ChartTooltip";

interface ReleaseTimelineProps {
  issues: IssueItem[];
  palette: Record<string, string>;
  highlightMilestone: string | null;
  variant: "compact" | "analytics";
  height?: number;
  onSelectMilestone: (title: string) => void;
}

function formatMonthTick(ms: number): string {
  const dt = new Date(ms);
  return dt.toLocaleDateString("en-US", {
    month: "short",
    year: "2-digit",
    timeZone: "UTC",
  });
}

export function ReleaseTimeline({
  issues,
  palette,
  highlightMilestone,
  variant,
  height: heightProp,
  onSelectMilestone,
}: ReleaseTimelineProps) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(900);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    setWidth(el.clientWidth || 900);
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        if (entry.contentRect.width > 0) {
          setWidth(Math.round(entry.contentRect.width));
        }
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const model = useMemo(
    () => buildMilestoneTimelineData(issues, palette, highlightMilestone),
    [issues, palette, highlightMilestone],
  );

  const height = heightProp ?? (variant === "compact" ? 76 : 136);
  const isSlim = height <= 90;
  const padX = 32;
  const bandTop = isSlim ? 15 : 22;
  const bandBottom = height - (isSlim ? 22 : 26);
  const railY = (bandTop + bandBottom) / 2;
  const offsetDelta = (bandBottom - bandTop) * 0.21;

  const ticks = useMemo(() => {
    if (!model) return [];
    const span = Math.max(model.maxTimeMs - model.minTimeMs, 1);
    const count = Math.max(3, Math.min(7, Math.floor(width / 145)));
    const result: Array<{ ms: number; label: string }> = [];
    for (let i = 0; i <= count; i += 1) {
      const ms = model.minTimeMs + (span * i) / count;
      result.push({ ms, label: formatMonthTick(ms) });
    }
    return result;
  }, [model, width]);

  if (!model) {
    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "0.65rem",
          width: "100%",
        }}
      >
        {variant === "compact" && (
          <span
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "0.66rem",
              fontWeight: 700,
              letterSpacing: "0.14em",
              color: "var(--muted)",
              flexShrink: 0,
              userSelect: "none",
            }}
          >
            RELEASES
          </span>
        )}
        <div
          ref={wrapRef}
          style={{
            position: "relative",
            flex: 1,
            minWidth: 0,
            height: `${height}px`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--muted)",
            fontSize: "0.82rem",
          }}
        >
          No milestones to display.
        </div>
      </div>
    );
  }

  const span = Math.max(model.maxTimeMs - model.minTimeMs, 1);
  const xFor = (ms: number): number =>
    padX + ((ms - model.minTimeMs) / span) * Math.max(width - padX * 2, 40);

  const nowX = xFor(model.nowTimeMs);
  const sepX = model.separatorTimeMs !== null ? xFor(model.separatorTimeMs) : null;
  const nowColor = palette.now_marker ?? "#dd2476";
  const highlightRing = palette.ms_highlight ?? "#f4a44a";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.65rem",
        width: "100%",
      }}
    >
      {variant === "compact" && (
        <span
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "0.66rem",
            fontWeight: 700,
            letterSpacing: "0.14em",
            color: "var(--muted)",
            flexShrink: 0,
            userSelect: "none",
          }}
        >
          RELEASES
        </span>
      )}
      <div ref={wrapRef} style={{ position: "relative", flex: 1, minWidth: 0 }}>
        <svg
          width="100%"
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          aria-label="Milestone release timeline"
          role="img"
          style={{ display: "block", overflow: "visible" }}
        >
          {/* Background track band */}
          <rect
            x={0}
            y={bandTop}
            width={width}
            height={bandBottom - bandTop}
            rx={8}
            fill="var(--chart-grid)"
          />
          {/* Vertical month grid ticks */}
          {ticks.map((tick, idx) => {
            const tx = xFor(tick.ms);
            const overlapsNow = Math.abs(tx - nowX) < 32;
            return (
              <g key={idx}>
                <line
                  x1={tx}
                  y1={bandTop}
                  x2={tx}
                  y2={bandBottom}
                  stroke="var(--chart-grid)"
                  strokeWidth={1}
                />
                {!overlapsNow && (
                  <text
                    x={tx}
                    y={height - 4}
                    textAnchor="middle"
                    fill="var(--muted)"
                    fontSize={9}
                    fontFamily="var(--font-mono)"
                  >
                    {tick.label}
                  </text>
                )}
              </g>
            );
          })}

          {/* Center rail */}
          <line
            x1={0}
            y1={railY}
            x2={width}
            y2={railY}
            stroke="var(--chart-axis)"
            strokeWidth={3}
          />

          {/* Separator for undated milestones */}
          {sepX !== null && (
            <g>
              <line
                x1={sepX}
                y1={bandTop}
                x2={sepX}
                y2={bandBottom}
                stroke="var(--muted)"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                opacity={0.7}
              />
              <text
                x={sepX}
                y={bandTop - 4}
                textAnchor="middle"
                fill="var(--muted)"
                fontSize={9}
                fontFamily="var(--font-mono)"
              >
                No due date
              </text>
            </g>
          )}

          {/* NOW vertical line */}
          <line
            x1={nowX}
            y1={bandTop}
            x2={nowX}
            y2={bandBottom}
            stroke={nowColor}
            strokeWidth={2}
          />
          <text
            x={nowX}
            y={height - 4}
            textAnchor="middle"
            fill={nowColor}
            fontSize={9}
            fontWeight={700}
            fontFamily="var(--font-mono)"
          >
            NOW
          </text>

          {/* Milestone markers */}
          {model.points.map((pt) => {
            const cx = xFor(pt.plotTimeMs);
            const cy = railY - pt.laneY * offsetDelta;
            const baseR = isSlim ? 5.5 : 6.5;
            const r = pt.isHighlighted ? baseR + 2 : baseR;
            const labelY = pt.laneY > 0 ? cy - r - 4 : cy + r + 9;
            return (
              <g
                key={pt.title}
                tabIndex={0}
                role="button"
                aria-label={`Milestone ${pt.title}, ${pt.status}, ${pt.closedCount} of ${pt.totalCount} closed`}
                aria-pressed={pt.isHighlighted}
                style={{
                  cursor: "pointer",
                  opacity: pt.isDimmed ? 0.28 : 1,
                  transition: "opacity 0.16s ease",
                }}
                onClick={() => onSelectMilestone(pt.title)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectMilestone(pt.title);
                  }
                }}
                onMouseEnter={(e) =>
                  setTooltip({
                    x: e.clientX,
                    y: e.clientY,
                    content: (
                      <div>
                        <strong>{pt.title}</strong>
                        <div>Due: {pt.dueDateLabel}</div>
                        <div>
                          Issues: {pt.closedCount}/{pt.totalCount}
                        </div>
                        <div>Status: {pt.status}</div>
                      </div>
                    ),
                  })
                }
                onMouseMove={(e) =>
                  setTooltip((prev) => (prev ? { ...prev, x: e.clientX, y: e.clientY } : null))
                }
                onMouseLeave={() => setTooltip(null)}
              >
                <circle
                  cx={cx}
                  cy={cy}
                  r={r + 4}
                  fill="transparent"
                />
                <circle
                  cx={cx}
                  cy={cy}
                  r={r}
                  fill={pt.color}
                  stroke={pt.isHighlighted ? highlightRing : "var(--bg-card)"}
                  strokeWidth={pt.isHighlighted ? 3 : 2}
                />
                <text
                  x={cx}
                  y={labelY}
                  textAnchor="middle"
                  fill="var(--text)"
                  fontSize={variant === "compact" ? 9.5 : 10}
                  fontWeight={pt.isHighlighted ? 700 : 600}
                >
                  {pt.title}
                </text>
              </g>
            );
          })}
        </svg>
        <ChartTooltip tooltip={tooltip} />
      </div>
    </div>
  );
}
