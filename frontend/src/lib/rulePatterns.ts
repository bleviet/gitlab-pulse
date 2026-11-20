export type PatternMode = "exact" | "contains" | "regex";

export interface ParsedPattern {
  mode: PatternMode;
  value: string;
}

const PREFIXES: Array<[PatternMode, string]> = [
  ["regex", "regex:"],
  ["contains", "contains:"],
  ["exact", "exact:"],
];

export function parsePattern(raw: string): ParsedPattern {
  for (const [mode, prefix] of PREFIXES) {
    if (raw.startsWith(prefix)) return { mode, value: raw.slice(prefix.length) };
  }
  return { mode: "exact", value: raw };
}

export function serializePattern(pattern: ParsedPattern): string {
  if (pattern.mode === "regex") return `regex:${pattern.value}`;
  if (pattern.mode === "contains") return `contains:${pattern.value}`;
  const needsPrefix = PREFIXES.some(([, prefix]) => pattern.value.startsWith(prefix));
  return needsPrefix ? `exact:${pattern.value}` : pattern.value;
}

export function describePattern(raw: string): string {
  const { mode, value } = parsePattern(raw);
  if (mode === "contains") return `contains "${value}"`;
  if (mode === "regex") return `pattern ${value}`;
  return value;
}

export function countMatchingLabels(raw: string, labelNames: string[]): number | null {
  const { mode, value } = parsePattern(raw);
  if (mode === "regex") return null;
  if (mode === "exact") return labelNames.filter((name) => name === value).length;
  return labelNames.filter((name) => name.includes(value)).length;
}
