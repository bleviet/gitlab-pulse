import { useEffect, useMemo, useRef, useState, type CSSProperties, type RefObject } from "react";
import { formatShare } from "../../lib/analytics";
import { buildMilestoneTimelineData, buildMonthTicks } from "../../lib/timeline";
import type { IssueItem } from "../../lib/types";
import { ChartTooltip, type TooltipState } from "./ChartTooltip";

interface ReleaseTimelineProps {
  issues: IssueItem[];
  palette: Record<string, string>;
  highlightMilestone: string | null;
  variant: "compact" | "analytics";
  height?: number;
  unscheduledCount: number;
  unscheduledOpenCount: number;
  isUnscheduledActive: boolean;
  onSelectMilestone: (title: string) => void;
  onSelectUnscheduled?: () => void;
  unscheduledExpanded?: boolean;
  unscheduledControlsId?: string;
  unscheduledTrayRef?: RefObject<HTMLButtonElement | null>;
}

const TRAY_WIDTH = 120;
const TRAY_WIDTH_COMPACT = 56;
const TRAY_GAP = 12;
const TRAY_COMPACT_BELOW = 520;
const CONTROL_CHAR_WIDTH = 5.6;
const TICK_LABEL_HALF_WIDTH = 16;
const CONTROL_GAP = 4;

interface EdgeControl {
  label: string;
  ariaLabel: string;
  side: "start" | "end";
  onActivate: () => void;
}

interface UnscheduledTrayProps {
  count: number;
  openCount: number;
  color: string;
  isActive: boolean;
  compact: boolean;
  top: number;
  height: number;
  onSelect?: () => void;
  expanded?: boolean;
  controlsId?: string;
  buttonRef?: RefObject<HTMLButtonElement | null>;
}

function UnscheduledTray({
  count,
  openCount,
  color,
  isActive,
  compact,
  top,
  height,
  onSelect,
  expanded,
  controlsId,
  buttonRef,
}: UnscheduledTrayProps) {
  const style: CSSProperties = {
    position: "absolute",
    top,
    right: 0,
    width: compact ? TRAY_WIDTH_COMPACT : TRAY_WIDTH,
    height,
    boxSizing: "border-box",
    display: "flex",
    alignItems: "center",
    justifyContent: compact ? "center" : "flex-start",
    gap: compact ? "0.3rem" : "0.45rem",
    padding: compact ? "0 0.3rem" : "0 0.5rem",
    border: isActive ? `1px solid ${color}` : "1px dashed var(--line-strong)",
    borderRadius: 10,
    background: "var(--surface)",
    textAlign: "left",
    font: "inherit",
    cursor: onSelect ? "pointer" : "default",
  };
  const openLabel = `${openCount} open ${openCount === 1 ? "issue" : "issues"}`;
  const content = (
    <>
      <span
        aria-hidden="true"
        style={{
          width: 14,
          height: 14,
          flexShrink: 0,
          boxSizing: "border-box",
          borderRadius: "50%",
          border: `1.5px dashed ${color}`,
        }}
      />
      {compact ? (
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.74rem",
            fontWeight: 600,
            color: "var(--heading)",
          }}
        >
          {count}
        </span>
      ) : (
        <span style={{ display: "flex", flexDirection: "column", minWidth: 0 }}>
          <span
            style={{
              fontSize: "0.74rem",
              fontWeight: 600,
              color: "var(--heading)",
              whiteSpace: "nowrap",
            }}
          >
            {count} unscheduled
          </span>
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.64rem",
              color: "var(--muted)",
              whiteSpace: "nowrap",
            }}
          >
            {openLabel}
          </span>
        </span>
      )}
    </>
  );
  if (onSelect) {
    return (
      <button
        ref={buttonRef}
        type="button"
        aria-label={`Show ${count} unscheduled milestones, ${openLabel}`}
        aria-haspopup={controlsId ? "dialog" : undefined}
        aria-expanded={controlsId ? Boolean(expanded) : undefined}
        aria-controls={controlsId}
        onClick={onSelect}
        style={style}
      >
        {content}
      </button>
    );
  }
  return <div style={style}>{content}</div>;
}

export function ReleaseTimeline({
  issues,
  palette,
  highlightMilestone,
  variant,
  height: heightProp,
  unscheduledCount,
  unscheduledOpenCount,
  isUnscheduledActive,
  onSelectMilestone,
  onSelectUnscheduled,
  unscheduledExpanded,
  unscheduledControlsId,
  unscheduledTrayRef,
}: ReleaseTimelineProps) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(900);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const [showAll, setShowAll] = useState(false);

  const model = useMemo(
    () => buildMilestoneTimelineData(issues, palette, highlightMilestone, undefined, showAll),
    [issues, palette, highlightMilestone, showAll],
  );
  const hasModel = model !== null;

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
  }, [hasModel]);

  const height = heightProp ?? (variant === "compact" ? 76 : 136);
  const isSlim = height <= 90;
  const padX = 32;
  const bandTop = isSlim ? 15 : 22;
  const bandBottom = height - (isSlim ? 22 : 26);
  const railY = (bandTop + bandBottom) / 2;
  const offsetDelta = (bandBottom - bandTop) * 0.21;

  const showTray = unscheduledCount > 0;
  const trayCompact = width < TRAY_COMPACT_BELOW;
  const trayWidth = trayCompact ? TRAY_WIDTH_COMPACT : TRAY_WIDTH;
  const scaleWidth = showTray ? width - trayWidth - TRAY_GAP : width;
  const trayActive = isUnscheduledActive || Boolean(unscheduledExpanded);
  const unscheduledColor = palette.ms_unscheduled ?? palette.neutral ?? "#7a8fa8";

  const ticks = useMemo(() => {
    if (!model) return [];
    const count = Math.max(3, Math.min(7, Math.floor(scaleWidth / 145)));
    return buildMonthTicks(model.minTimeMs, model.maxTimeMs, count);
  }, [model, scaleWidth]);

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
          <span style={{ paddingRight: unscheduledCount > 0 ? trayWidth + TRAY_GAP : 0 }}>
            {unscheduledCount > 0 ? "No milestones with a due date." : "No milestones to display."}
          </span>
          {unscheduledCount > 0 && (
            <UnscheduledTray
              count={unscheduledCount}
              openCount={unscheduledOpenCount}
              color={unscheduledColor}
              isActive={trayActive}
            compact={trayCompact}
            expanded={unscheduledExpanded}
            controlsId={unscheduledControlsId}
            buttonRef={unscheduledTrayRef}
              top={bandTop}
              height={bandBottom - bandTop}
              onSelect={onSelectUnscheduled}
            />
          )}
        </div>
      </div>
    );
  }

  const span = Math.max(model.maxTimeMs - model.minTimeMs, 1);
  const xFor = (ms: number): number =>
    padX + ((ms - model.minTimeMs) / span) * Math.max(scaleWidth - padX * 2, 40);

  const nowX = xFor(model.nowTimeMs);
  const nowColor = palette.now_marker ?? "#dd2476";
  const highlightRing = palette.ms_highlight ?? "#f4a44a";

  const controls: EdgeControl[] = [];
  if (showAll) {
    if (model.outOfWindowCount > 0) {
      controls.push({
        label: "1 year ›",
        ariaLabel: "Show one-year window",
        side: "end",
        onActivate: () => setShowAll(false),
      });
    }
  } else {
    if (model.hiddenEarlierCount > 0) {
      controls.push({
        label: `‹ ${model.hiddenEarlierCount} earlier`,
        ariaLabel: `Show ${model.hiddenEarlierCount} earlier releases`,
        side: "start",
        onActivate: () => setShowAll(true),
      });
    }
    if (model.hiddenLaterCount > 0) {
      controls.push({
        label: `${model.hiddenLaterCount} later ›`,
        ariaLabel: `Show ${model.hiddenLaterCount} later releases`,
        side: "end",
        onActivate: () => setShowAll(true),
      });
    }
  }
  const collidesWithControl = (tx: number): boolean =>
    controls.some((c) => {
      const w = c.label.length * CONTROL_CHAR_WIDTH + CONTROL_GAP + TICK_LABEL_HALF_WIDTH;
      return c.side === "start" ? tx < w : tx > scaleWidth - w;
    });

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
            width={scaleWidth}
            height={bandBottom - bandTop}
            rx={8}
            fill="var(--chart-grid)"
          />
          {/* Vertical month grid ticks */}
          {ticks.map((tick, idx) => {
            const tx = xFor(tick.ms);
            const hideLabel = Math.abs(tx - nowX) < 32 || collidesWithControl(tx);
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
                {!hideLabel && (
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
            x2={scaleWidth}
            y2={railY}
            stroke="var(--chart-axis)"
            strokeWidth={3}
          />

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

          {controls.map((c) => (
            <text
              key={c.side}
              x={c.side === "start" ? 0 : scaleWidth}
              y={height - 4}
              textAnchor={c.side}
              fill="var(--muted)"
              fontSize={9}
              fontFamily="var(--font-mono)"
              tabIndex={0}
              role="button"
              aria-label={c.ariaLabel}
              style={{ cursor: "pointer" }}
              onClick={c.onActivate}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  c.onActivate();
                }
              }}
            >
              {c.label}
            </text>
          ))}

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
                          Issues: {pt.closedCount}/{pt.totalCount} closed ({formatShare(pt.closedCount, pt.totalCount)})
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
        {showTray && (
          <UnscheduledTray
            count={unscheduledCount}
            openCount={unscheduledOpenCount}
            color={unscheduledColor}
            isActive={trayActive}
              compact={trayCompact}
              expanded={unscheduledExpanded}
              controlsId={unscheduledControlsId}
              buttonRef={unscheduledTrayRef}
            top={bandTop}
            height={bandBottom - bandTop}
            onSelect={onSelectUnscheduled}
          />
        )}
        <ChartTooltip tooltip={tooltip} />
      </div>
    </div>
  );
}
