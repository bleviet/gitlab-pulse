import { useState } from "react";
import { formatShare, type DonutModel } from "../../lib/analytics";
import { contrastTextForHex } from "../../lib/colors";
import type { ValueMode } from "../../lib/types";
import { ChartTooltip, type TooltipState } from "./ChartTooltip";

interface PriorityDonutProps {
  model: DonutModel;
  centerCaption: string;
  ariaLabel: string;
  emptyMessage: string;
  centerTooltipSubject: string;
  size?: number;
  valueMode: ValueMode;
  activeSlice: string | null;
  isCenterSelected: boolean;
  showLegend?: boolean;
  onSelectSlice: (label: string) => void;
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
  model,
  centerCaption,
  ariaLabel,
  emptyMessage,
  centerTooltipSubject,
  size = 112,
  valueMode,
  activeSlice,
  isCenterSelected,
  showLegend = true,
  onSelectSlice,
  onSelectCenter,
}: PriorityDonutProps) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  if (model.total === 0) {
    return (
      <div
        style={{
          height: `${size}px`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "var(--muted)",
          fontSize: "0.78rem",
        }}
      >
        {emptyMessage}
      </div>
    );
  }

  const cx = size / 2;
  const cy = size / 2;
  const outerR = Math.round(size * 0.46);
  const innerR = Math.round(size * 0.25);

  const sliceFont = size >= 120 ? 8.5 : 8;

  let cursor = 0;
  const segments = model.slices.map((slice) => {
    const sweep = (slice.count / model.total) * 360;
    const startDeg = cursor;
    const endDeg = cursor + sweep;
    cursor = endDeg;
    const midDeg = startDeg + sweep / 2;
    const isHovered = hovered === slice.label;
    const isSelected = activeSlice !== null && activeSlice.toLowerCase() === slice.label.toLowerCase();
    const isDimmed =
      !isCenterSelected &&
      activeSlice !== null &&
      activeSlice.toLowerCase() !== slice.label.toLowerCase();

    const shift = isHovered ? 4 : 0;
    const shiftVec = polarToCartesian(0, 0, shift, midDeg);
    const labelPos = polarToCartesian(cx, cy, (outerR + innerR) / 2, midDeg);
    const arcPx = ((sweep * Math.PI) / 180) * ((outerR + innerR) / 2);
    const labelText =
      valueMode === "percent" ? formatShare(slice.count, model.total) : String(slice.count);
    const labelWidth = labelText.length * (sliceFont * 0.62) + 4;
    const showLabel =
      arcPx >= Math.max(16, labelWidth) && outerR - innerR - 3 >= labelWidth * 0.85;

    return {
      ...slice,
      startDeg,
      endDeg,
      shiftVec,
      labelPos,
      showLabel,
      labelText,
      isSelected,
      isDimmed,
    };
  });

  const captionLines = centerCaption.split("\n");
  const totalFont = Math.max(14, Math.round(size * 0.135));
  const captionFont = Math.max(7, Number((size * 0.062).toFixed(1)));

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: "0.3rem",
        minWidth: 0,
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        aria-label={ariaLabel}
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
              strokeWidth={1.5}
            />
            {seg.showLabel && (
              <text
                x={seg.labelPos.x}
                y={seg.labelPos.y}
                textAnchor="middle"
                dominantBaseline="central"
                fill={contrastTextForHex(seg.color)}
                fontSize={sliceFont}
                fontWeight={700}
                fontFamily="var(--font-mono)"
                letterSpacing="-0.03em"
                style={{ pointerEvents: "none" }}
              >
                {seg.labelText}
              </text>
            )}
          </g>
        ))}

        {/* Clickable center hole */}
        <g
          tabIndex={0}
          role="button"
          aria-label={`Select all ${centerTooltipSubject} issues (${model.total})`}
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
                  Click to filter all <strong>{centerTooltipSubject}</strong> issues ({model.total})
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
            y={cy - (captionLines.length > 1 ? 8 : 5)}
            textAnchor="middle"
            dominantBaseline="central"
            fill="var(--heading)"
            fontFamily="var(--font-display)"
            fontWeight={700}
            fontSize={totalFont}
          >
            {model.total}
          </text>
          {captionLines.map((line, idx) => (
            <text
              key={line}
              x={cx}
              y={cy + 6.5 + idx * 8.5}
              textAnchor="middle"
              dominantBaseline="central"
              fill="var(--muted)"
              fontFamily="var(--font-body)"
              fontWeight={600}
              fontSize={captionFont}
              letterSpacing="0.06em"
            >
              {line}
            </text>
          ))}
        </g>
      </svg>

      {showLegend && (
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            gap: "0.18rem 0.48rem",
            maxWidth: "100%",
          }}
        >
          {segments.map((seg) => (
            <button
              key={seg.label}
              type="button"
              aria-pressed={seg.isSelected}
              onClick={() => onSelectSlice(seg.label)}
              style={{
                border: "none",
                background: "transparent",
                padding: "0 2px",
                display: "inline-flex",
                alignItems: "center",
                gap: "0.24rem",
                cursor: "pointer",
                fontSize: "0.68rem",
                lineHeight: 1.3,
                color: seg.isSelected ? "var(--heading)" : "var(--muted)",
                fontWeight: seg.isSelected ? 700 : 500,
                opacity: seg.isDimmed ? 0.35 : 1,
                transition: "opacity 0.16s ease",
              }}
            >
              <span
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: 999,
                  background: seg.color,
                  flexShrink: 0,
                }}
              />
              <span>
                {seg.label}
                {valueMode === "percent" ? ` ${formatShare(seg.count, model.total)}` : ""}
              </span>
            </button>
          ))}
        </div>
      )}
      <ChartTooltip tooltip={tooltip} />
    </div>
  );
}
