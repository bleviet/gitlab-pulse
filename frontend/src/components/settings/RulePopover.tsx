import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

interface RulePopoverProps {
  id: string;
  title: string;
  anchor: HTMLElement | null;
  placement?: "right" | "bottom";
  wide?: boolean;
  headerExtra?: ReactNode;
  subtitle?: string;
  onClose: () => void;
  children: ReactNode;
}

interface PopoverPosition {
  top: number;
  left: number;
  width: number;
  maxHeight: number;
}

function computePosition(
  anchor: HTMLElement | null,
  placement: "right" | "bottom",
  wide: boolean,
): PopoverPosition {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const margin = 12;
  const desiredWidth = wide ? 600 : 460;
  const width = Math.min(desiredWidth, vw - margin * 2);

  if (vw < 640 || !anchor || !anchor.isConnected) {
    const top = Math.min(104, Math.max(margin, vh * 0.1));
    return {
      top,
      left: Math.max(margin, Math.round((vw - width) / 2)),
      width,
      maxHeight: Math.max(240, vh - top - margin),
    };
  }

  const triggerRect = anchor.getBoundingClientRect();
  const panelEl = anchor.closest<HTMLElement>(".pulse-panel");
  const panelRect = panelEl?.getBoundingClientRect() ?? triggerRect;

  if (placement === "right") {
    const rightSpace = vw - panelRect.right - margin * 2;
    if (rightSpace >= Math.min(width, 380)) {
      const fittedWidth = Math.min(width, rightSpace);
      const top = Math.max(54, Math.min(panelRect.top, vh - 320));
      return {
        top: Math.round(top),
        left: Math.round(panelRect.right + 10),
        width: Math.round(fittedWidth),
        maxHeight: Math.max(240, Math.round(vh - top - margin)),
      };
    }
  }

  const belowTop = triggerRect.bottom + 8;
  const spaceBelow = vh - belowTop - margin;
  const top = spaceBelow >= 260 ? belowTop : Math.max(54, vh - Math.min(540, vh - 68) - margin);
  const idealLeft = triggerRect.left;
  const left = Math.max(margin, Math.min(idealLeft, vw - width - margin));

  return {
    top: Math.round(top),
    left: Math.round(left),
    width: Math.round(width),
    maxHeight: Math.max(240, Math.round(vh - top - margin)),
  };
}

export function RulePopover({
  id,
  title,
  anchor,
  placement = "bottom",
  wide = false,
  headerExtra,
  subtitle,
  onClose,
  children,
}: RulePopoverProps) {
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const [pos, setPos] = useState<PopoverPosition>(() => computePosition(anchor, placement, wide));

  useLayoutEffect(() => {
    const update = () => setPos(computePosition(anchor, placement, wide));
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [anchor, placement, wide]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !e.defaultPrevented) {
        onClose();
        anchor?.focus();
      }
    };
    const onPointerDown = (e: PointerEvent) => {
      const target = e.target as HTMLElement | null;
      if (!target) return;
      if (popoverRef.current?.contains(target)) return;
      if (anchor?.contains(target)) return;
      if (target.closest("[data-rule-trigger]")) return;
      if (target.closest(".edit-mode-bar")) return;
      onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    document.addEventListener("pointerdown", onPointerDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.removeEventListener("pointerdown", onPointerDown);
    };
  }, [anchor, onClose]);

  const content = (
    <div
      id={`rule-popover-${id}`}
      ref={popoverRef}
      className="rule-popover"
      role="dialog"
      aria-label={title}
      style={{
        top: pos.top,
        left: pos.left,
        width: pos.width,
        maxHeight: pos.maxHeight,
      }}
    >
      <div className="rule-popover-head">
        <div className="rule-popover-head-left">
          <span className="pulse-panel-title">{title}</span>
          {headerExtra}
        </div>
        <button
          type="button"
          className="pulse-icon-btn rule-popover-close"
          aria-label={`Close ${title}`}
          onClick={() => {
            onClose();
            anchor?.focus();
          }}
        >
          <X size={13} />
        </button>
      </div>
      {subtitle && <p className="rule-popover-subtitle">{subtitle}</p>}
      <div className="rule-popover-body">{children}</div>
    </div>
  );

  return createPortal(content, document.body);
}
