import { useEffect, useMemo, useRef, useState } from "react";
import { buildDailyVelocityData } from "../../lib/analytics";
import type { IssueItem } from "../../lib/types";
import { ChartTooltip, type TooltipState } from "./ChartTooltip";

interface DailyVelocityChartProps {
  issues: IssueItem[];
  palette: Record<string, string>;
  activeDay: string | null;
  activeDayKind: "created" | "closed" | null;
  onSelectPoint: (isoDate: string, kind: "created" | "closed") => void;
}

export function DailyVelocityChart({
  issues,
  palette,
  activeDay,
  activeDayKind,
  onSelectPoint,
}: DailyVelocityChartProps) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(520);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    setWidth(el.clientWidth || 520);
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

  const days = useMemo(() => buildDailyVelocityData(issues), [issues]);
  const height = 152;
  const padL = 28;
  const padR = 20;
  const padT = 26;
  const padB = 26;
  const innerW = Math.max(width - padL - padR, 40);
  const innerH = height - padT - padB;

  const maxVal = Math.max(...days.flatMap((d) => [d.created, d.closed]), 1);
  const xFor = (idx: number): number => padL + (idx / Math.max(days.length - 1, 1)) * innerW;
  const yFor = (val: number): number => padT + innerH - (val / maxVal) * innerH;

  const createdColor = palette.opened ?? "#4facfe";
  const closedColor = palette.closed ?? "#56d4b0";

  const createdPath = days
    .map((d, idx) => `${idx === 0 ? "M" : "L"} ${xFor(idx)} ${yFor(d.created)}`)
    .join(" ");
  const closedPath = days
    .map((d, idx) => `${idx === 0 ? "M" : "L"} ${xFor(idx)} ${yFor(d.closed)}`)
    .join(" ");

  return (
    <div ref={wrapRef} style={{ position: "relative", width: "100%" }}>
      <div
        style={{
          position: "absolute",
          top: 0,
          right: 4,
          display: "flex",
          gap: "0.85rem",
          fontSize: "0.74rem",
          color: "var(--muted)",
          pointerEvents: "none",
        }}
      >
        <span style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
          <span style={{ width: 8, height: 8, borderRadius: 999, background: createdColor }} />
          New
        </span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: "0.3rem" }}>
          <span style={{ width: 8, height: 8, borderRadius: 999, background: closedColor }} />
          Closed
        </span>
      </div>
      <svg
        width="100%"
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        aria-label="Daily new versus closed issues line chart"
        role="img"
        style={{ display: "block" }}
      >
        {/* Horizontal baseline */}
        <line
          x1={padL}
          y1={padT + innerH}
          x2={width - padR}
          y2={padT + innerH}
          stroke="var(--chart-grid)"
          strokeWidth={1}
        />

        <path d={createdPath} fill="none" stroke={createdColor} strokeWidth={2.2} />
        <path d={closedPath} fill="none" stroke={closedColor} strokeWidth={2.2} />

        {days.map((d, idx) => {
          const cx = xFor(idx);
          const cyCreated = yFor(d.created);
          const cyClosed = yFor(d.closed);
          const isCreatedActive = activeDay === d.isoDate && activeDayKind === "created";
          const isClosedActive = activeDay === d.isoDate && activeDayKind === "closed";

          return (
            <g key={d.isoDate}>
              <text
                x={cx}
                y={height - 6}
                textAnchor="middle"
                fill="var(--muted)"
                fontSize={10}
                fontFamily="var(--font-mono)"
              >
                {d.label}
              </text>

              {/* Created point */}
              <g
                tabIndex={0}
                role="button"
                aria-label={`${d.label}: ${d.created} new issues`}
                aria-pressed={isCreatedActive}
                style={{ cursor: "pointer" }}
                onClick={() => onSelectPoint(d.isoDate, "created")}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectPoint(d.isoDate, "created");
                  }
                }}
                onMouseEnter={(e) =>
                  setTooltip({
                    x: e.clientX,
                    y: e.clientY,
                    content: (
                      <div>
                        <strong>{d.label}</strong> — New: {d.created}
                      </div>
                    ),
                  })
                }
                onMouseMove={(e) =>
                  setTooltip((prev) => (prev ? { ...prev, x: e.clientX, y: e.clientY } : null))
                }
                onMouseLeave={() => setTooltip(null)}
              >
                <circle cx={cx} cy={cyCreated} r={10} fill="transparent" />
                <circle
                  cx={cx}
                  cy={cyCreated}
                  r={isCreatedActive ? 6 : 4.2}
                  fill={createdColor}
                  stroke={isCreatedActive ? "var(--heading)" : "var(--chart-bg)"}
                  strokeWidth={2}
                />
                {d.created > 0 && (
                  <text
                    x={cx}
                    y={cyCreated - 9}
                    textAnchor="middle"
                    fill="var(--text)"
                    fontSize={10}
                    fontWeight={700}
                    fontFamily="var(--font-mono)"
                  >
                    {d.created}
                  </text>
                )}
              </g>

              {/* Closed point */}
              <g
                tabIndex={0}
                role="button"
                aria-label={`${d.label}: ${d.closed} closed issues`}
                aria-pressed={isClosedActive}
                style={{ cursor: "pointer" }}
                onClick={() => onSelectPoint(d.isoDate, "closed")}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onSelectPoint(d.isoDate, "closed");
                  }
                }}
                onMouseEnter={(e) =>
                  setTooltip({
                    x: e.clientX,
                    y: e.clientY,
                    content: (
                      <div>
                        <strong>{d.label}</strong> — Closed: {d.closed}
                      </div>
                    ),
                  })
                }
                onMouseMove={(e) =>
                  setTooltip((prev) => (prev ? { ...prev, x: e.clientX, y: e.clientY } : null))
                }
                onMouseLeave={() => setTooltip(null)}
              >
                <circle cx={cx} cy={cyClosed} r={10} fill="transparent" />
                <circle
                  cx={cx}
                  cy={cyClosed}
                  r={isClosedActive ? 6 : 4.2}
                  fill={closedColor}
                  stroke={isClosedActive ? "var(--heading)" : "var(--chart-bg)"}
                  strokeWidth={2}
                />
                {d.closed > 0 && (
                  <text
                    x={cx}
                    y={cyClosed + (Math.abs(cyClosed - cyCreated) < 14 ? 14 : -9)}
                    textAnchor="middle"
                    fill="var(--text)"
                    fontSize={10}
                    fontWeight={700}
                    fontFamily="var(--font-mono)"
                  >
                    {d.closed}
                  </text>
                )}
              </g>
            </g>
          );
        })}
      </svg>
      <ChartTooltip tooltip={tooltip} />
    </div>
  );
}
