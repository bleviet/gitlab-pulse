import type { IssueItem, LabelStyle } from "./types";

export interface LabelInventoryItem {
  name: string;
  color: string | null;
  textColor: string | null;
  count: number;
}

export function buildLabelInventory(
  issues: IssueItem[],
  labelStyles: Record<string, LabelStyle>,
): LabelInventoryItem[] {
  const counts = new Map<string, number>();
  for (const issue of issues) {
    for (const label of new Set(issue.labels)) {
      counts.set(label, (counts.get(label) ?? 0) + 1);
    }
  }
  for (const name of Object.keys(labelStyles)) {
    if (!counts.has(name)) counts.set(name, 0);
  }
  const items: LabelInventoryItem[] = [];
  for (const [name, count] of counts) {
    const style = labelStyles[name];
    items.push({
      name,
      color: style?.color ?? null,
      textColor: style?.text_color ?? null,
      count,
    });
  }
  return items.sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
}
