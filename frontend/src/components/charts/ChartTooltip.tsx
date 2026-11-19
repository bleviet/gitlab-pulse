import { useLayoutEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

export interface TooltipState {
  x: number;
  y: number;
  content: ReactNode;
}

interface Size {
  width: number;
  height: number;
}

/**
 * Places a tooltip box next to the cursor without covering it.
 *
 * The box goes right of and below the cursor, flips to the other side when it
 * would overflow the viewport, then is clamped into the viewport.
 *
 * @param cursor Cursor position in viewport coordinates.
 * @param size Measured tooltip size.
 * @param viewport Viewport size.
 * @param offset Gap between the cursor and the box.
 * @param margin Minimum distance from the viewport edges.
 * @returns Top-left corner of the tooltip box.
 */
export function placeTooltip(
  cursor: { x: number; y: number },
  size: Size,
  viewport: Size,
  offset = 14,
  margin = 8,
): { left: number; top: number } {
  let left = cursor.x + offset;
  if (left + size.width > viewport.width - margin) {
    left = cursor.x - offset - size.width;
  }
  let top = cursor.y + offset;
  if (top + size.height > viewport.height - margin) {
    top = cursor.y - offset - size.height;
  }
  return {
    left: Math.max(margin, Math.min(left, viewport.width - size.width - margin)),
    top: Math.max(margin, Math.min(top, viewport.height - size.height - margin)),
  };
}

export function ChartTooltip({ tooltip }: { tooltip: TooltipState | null }) {
  const ref = useRef<HTMLDivElement | null>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!tooltip || !el) return;
    // Measure at the origin: a fixed box shrinks to fit the space right of its last position.
    el.style.left = "0px";
    el.style.top = "0px";
    const { left, top } = placeTooltip(
      { x: tooltip.x, y: tooltip.y },
      { width: el.offsetWidth, height: el.offsetHeight },
      { width: window.innerWidth, height: window.innerHeight },
    );
    el.style.left = `${left}px`;
    el.style.top = `${top}px`;
  }, [tooltip]);

  if (!tooltip) return null;
  // Portal to body so scrolling or layered chart containers (e.g. the unscheduled
  // milestones popover) cannot clip the tooltip or cap its z-index.
  return createPortal(
    <div ref={ref} className="chart-tooltip" role="status">
      {tooltip.content}
    </div>,
    document.body,
  );
}
