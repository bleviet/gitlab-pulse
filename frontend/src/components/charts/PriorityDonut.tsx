import { useMemo, useState } from "react";
import { buildPriorityDonutData } from "../../lib/analytics";
import type { IssueItem, ThemeMode } from "../../lib/types";
import { ChartTooltip, type TooltipState } from "./ChartTooltip";

interface PriorityDonutProps {
  issues: IssueItem[];
  stateFilter: "opened" | "closed";
  centerCaption: string;
  palette: Record<string, string>;
  priorityOrder: string[];
  theme: ThemeMode;
  activePriority: string | null;
  isCenterSelected: boolean;
  onSelectSlice: (priority: string) => void;
  onSelectCenter: () => void;
}

function polarToCartesian(cx: number, cy: number, radius: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(rad),
    y: cy + radius * Math.sin(rad),
  };
}

function donutArcPath(
  cx: number,
  cy: number,
  outerR: number,
  innerR: number,
  startDeg: number,
  endDeg: number,
): string {
  const clampedEnd = endDeg - startDeg >= 359.99 ? startDeg + 359.99 : endDeg;
  const largeArc = clampedEnd - startDeg > 180 ? 1 : 0;
  const p1 = polarToCartesian(cx, cy, outerR, startDeg);
  const p2 = polarToCartesian(cx, cy, outerR, clampedEnd);
  const p3 = polarToCartesian(cx, cy, innerR, clampedEnd);
  const p4 = polarToCartesian(cx, cy, innerR, startDeg);

  return [
    `M ${p1.x} ${p1.y}`,
    `A ${outerR} ${outerR} 0 ${largeArc} 1 ${p2.x} ${p2.y}`,
    `L ${p3.x} ${p3.y}`,
    `A ${innerR} ${innerR} 0 ${largeArc} 0 ${p4.x} ${p4.y}`,
    "Z",
  ].join(" ");
}

export function PriorityDonut({
  issues,
  stateFilter,
  centerCaption,
  palette,
  priorityOrder,
  theme,
  activePriority,
  isCenterSelected,
  onSelectSlice,
  onSelectCenter,
}: PriorityDonutProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  const model = useMemo(
    () => buildPriorityDonutData(issues, stateFilter, palette, priorityOrder, theme),
    [issues, stateFilter, palette, priorityOrder, theme],
  );

  if (model.total === 0) {
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
        No {stateFilter} issues.
      </div>
    );
  }

  const size = 152;
  const cx = size / 2;
  const cy = size / 2;
  const outerR = 66;
  const innerR = 39;

  let cursor = 0;
  const segments = model.slices.map((slice) => {
    const sweep = (slice.count / model.total) * 360;
    const startDeg = cursor;
    const endDeg = cursor + sweep;
    cursor = endDeg;
    const midDeg = startDeg + sweep / 2;
    const isHovered = hovered === slice.label;
    const isSelected = activePriority !== null && activePriority.toLowerCase() === slice.label.toLowerCase();
    const isDimmed =
      !isCenterSelected &&
      activePriority !== null &&
      activePriority.toLowerCase() !== slice.label.toLowerCase();

    const shift = isHovered ? 5 : 0;
    const shiftVec = polarToCartesian(0, 0, shift, midDeg);
    const labelPos = polarToCartesian(cx, cy, (outerR + innerR) / 2, midDeg);
    const arcPx = ((sweep * Math.PI) / 180) * ((outerR + innerR) / 2);
    const showLabel = arcPx >= 16;

    return {
      ...slice,
      startDeg,
      endDeg,
      shiftVec,
      labelPos,
      showLabel,
      isSelected,
      isDimmed,
    };
  });

  const captionLines = centerCaption.split("\n");

  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "152px" }}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        aria-label={`${stateFilter} issues by priority donut chart`}
        role="img"
        style={{ overflow: "visible" }}
      >
        {segments.map((seg) => (
          <g
            key={seg.label}
            tabIndex={0}
            role="button"
            aria-label={`${seg.label}: ${seg.count} issues`}
            aria-pressed={seg.isSelected}
            transform={`translate(${seg.shiftVec.x}, ${seg.shiftVec.y})`}
            style={{
              cursor: "pointer",
              opacity: seg.isDimmed ? 0.28 : 1,
              transition: "transform 0.16s ease, opacity 0.16s ease",
            }}
            onClick={() => onSelectSlice(seg.label)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelectSlice(seg.label);
              }
            }}
            onMouseEnter={(e) => {
              setHovered(seg.label);
              setTooltip({
                x: e.clientX,
                y: e.clientY,
                content: (
                  <div>
                    <strong>{seg.label}</strong>: {seg.count} issues (
                    {Math.round((seg.count / model.total) * 100)}%)
                  </div>
                ),
              });
            }}
            onMouseMove={(e) =>
              setTooltip((prev) => (prev ? { ...prev, x: e.clientX, y: e.clientY } : null))
            }
            onMouseLeave={() => {
              setHovered(null);
              setTooltip(null);
            }}
          >
            <path
              d={donutArcPath(cx, cy, outerR, innerR, seg.startDeg, seg.endDeg)}
              fill={seg.color}
              stroke="var(--chart-bg)"
              strokeWidth={2}
            />
            {seg.showLabel && (
              <text
                x={seg.labelPos.x}
                y={seg.labelPos.y}
                textAnchor="middle"
                dominantBaseline="central"
                fill="#ffffff"
                fontSize={10}
                fontWeight={700}
                fontFamily="var(--font-mono)"
                style={{ pointerEvents: "none" }}
              >
                {seg.count}
              </text>
            )}
          </g>
        ))}

        {/* Clickable center hole */}
        <g
          tabIndex={0}
          role="button"
          aria-label={`Select all ${stateFilter} issues (${model.total})`}
          aria-pressed={isCenterSelected}
          style={{ cursor: "pointer" }}
          onClick={onSelectCenter}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              onSelectCenter();
            }
          }}
          onMouseEnter={(e) =>
            setTooltip({
              x: e.clientX,
              y: e.clientY,
              content: (
                <div>
                  Click to filter all <strong>{stateFilter}</strong> issues ({model.total})
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
            r={innerR - 2}
            fill={isCenterSelected ? "var(--accent-soft)" : "transparent"}
            stroke={isCenterSelected ? "var(--accent)" : "transparent"}
            strokeWidth={1.5}
          />
          <text
            x={cx}
            y={cy - (captionLines.length > 1 ? 10 : 6)}
            textAnchor="middle"
            dominantBaseline="central"
            fill="var(--heading)"
            fontFamily="var(--font-display)"
            fontWeight={700}
            fontSize={20}
          >
            {model.total}
          </text>
          {captionLines.map((line, idx) => (
            <text
              key={line}
              x={cx}
              y={cy + 9 + idx * 10}
              textAnchor="middle"
              dominantBaseline="central"
              fill="var(--muted)"
              fontFamily="var(--font-body)"
              fontWeight={600}
              fontSize={8.5}
              letterSpacing="0.06em"
            >
              {line}
            </text>
          ))}
        </g>
      </svg>
      <ChartTooltip tooltip={tooltip} />
    </div>
  );
}
