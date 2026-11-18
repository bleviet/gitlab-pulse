import { CalendarOff, CheckCircle2, Circle, PlusCircle, Tag, UserX } from "lucide-react";
import type { SummaryGroup, SummaryItem } from "../lib/summary";
import type { IssueFacets } from "../lib/types";

interface SummaryBarProps {
  groups: SummaryGroup[];
  activeSummaryId: string | null;
  facets: IssueFacets;
  onSelectSummary: (item: SummaryItem, isCurrentlyActive: boolean) => void;
}

function facetsEqual(a: IssueFacets, b: IssueFacets): boolean {
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]) as Set<keyof IssueFacets>;
  for (const key of keys) {
    if (key === "query") continue;
    if ((a[key] ?? undefined) !== (b[key] ?? undefined)) {
      return false;
    }
  }
  return true;
}

function renderIcon(icon: SummaryItem["icon"], dotColor?: string) {
  if (dotColor) {
    return <span className="prio-dot" style={{ background: dotColor }} aria-hidden="true" />;
  }
  switch (icon) {
    case "circle":
      return <Circle size={12} aria-hidden="true" />;
    case "plus":
      return <PlusCircle size={12} aria-hidden="true" />;
    case "check":
      return <CheckCircle2 size={12} aria-hidden="true" />;
    case "milestone":
      return <CalendarOff size={12} aria-hidden="true" />;
    case "user-x":
      return <UserX size={12} aria-hidden="true" />;
    case "tag":
      return <Tag size={12} aria-hidden="true" />;
    default:
      return null;
  }
}

export function SummaryBar({
  groups,
  activeSummaryId,
  facets,
  onSelectSummary,
}: SummaryBarProps) {
  return (
    <div className="issue-summary-bar" role="region" aria-label="Summary quick filters">
      {groups.map((group, groupIndex) => (
        <div
          key={group.heading}
          role="group"
          aria-label={group.heading}
          style={{ display: "inline-flex", alignItems: "center", flexWrap: "wrap", gap: "0.3rem" }}
        >
          {groupIndex > 0 && <span className="summary-divider" aria-hidden="true" />}
          {group.items.map((item) => {
            const isActive =
              activeSummaryId === item.itemId ||
              (activeSummaryId === null && facetsEqual(facets, item.facets));
            return (
              <button
                key={item.itemId}
                type="button"
                className="summary-pill"
                aria-pressed={isActive}
                onClick={() => onSelectSummary(item, isActive)}
              >
                {renderIcon(item.icon, item.dotColor)}
                <span>{item.label}</span>
                <strong>{item.value.toLocaleString()}</strong>
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}
