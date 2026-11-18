import type { ReactNode } from "react";

export interface TooltipState {
  x: number;
  y: number;
  content: ReactNode;
}

export function ChartTooltip({ tooltip }: { tooltip: TooltipState | null }) {
  if (!tooltip) return null;
  const clampedLeft = Math.min(tooltip.x + 14, window.innerWidth - 240);
  const clampedTop = Math.max(8, tooltip.y - 18);
  return (
    <div
      className="chart-tooltip"
      role="status"
      style={{
        left: `${clampedLeft}px`,
        top: `${clampedTop}px`,
      }}
    >
      {tooltip.content}
    </div>
  );
}
