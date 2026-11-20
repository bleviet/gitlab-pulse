import { useMemo, useState, type CSSProperties, type KeyboardEvent } from "react";
import { X } from "lucide-react";
import type { LabelInventoryItem } from "../../lib/labelInventory";
import {
  countMatchingLabels,
  describePattern,
  parsePattern,
  serializePattern,
} from "../../lib/rulePatterns";

interface MatcherInputProps {
  id: string;
  kind: "label" | "title";
  value: string[];
  onChange: (next: string[]) => void;
  inventory: LabelInventoryItem[];
  disabled?: boolean;
  problems?: Record<number, string>;
  ariaLabel: string;
  matchCounts?: Record<string, number>;
}

type MatcherOption =
  | { kind: "label"; key: string; item: LabelInventoryItem }
  | { kind: "contains"; key: string; text: string; matches: number }
  | { kind: "new"; key: string; text: string };

const MAX_OPTIONS = 40;

function chipStyle(
  raw: string,
  byName: Map<string, LabelInventoryItem>,
): CSSProperties | undefined {
  const { mode, value } = parsePattern(raw);
  const item = mode === "exact" ? byName.get(value) : undefined;
  if (!item?.color) return undefined;
  return {
    background: item.color,
    color: item.textColor ?? undefined,
    borderColor: item.color,
  };
}

export function MatcherInput({
  id,
  kind,
  value,
  onChange,
  inventory,
  disabled,
  problems,
  ariaLabel,
  matchCounts,
}: MatcherInputProps) {
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  const [advancedText, setAdvancedText] = useState("");

  const byName = useMemo(() => new Map(inventory.map((i) => [i.name, i])), [inventory]);
  const labelNames = useMemo(() => inventory.map((i) => i.name), [inventory]);

  const options = useMemo<MatcherOption[]>(() => {
    if (kind !== "label") return [];
    const text = query.trim();
    const needle = text.toLowerCase();
    const selected = new Set(value);
    const result: MatcherOption[] = inventory
      .filter((item) => !selected.has(serializePattern({ mode: "exact", value: item.name })))
      .filter((item) => !needle || item.name.toLowerCase().includes(needle))
      .slice(0, MAX_OPTIONS)
      .map((item) => ({ kind: "label", key: `label:${item.name}`, item }));
    if (text) {
      result.push({
        kind: "contains",
        key: "contains",
        text,
        matches: countMatchingLabels(`contains:${text}`, labelNames) ?? 0,
      });
      if (!byName.has(text) && !selected.has(serializePattern({ mode: "exact", value: text }))) {
        result.push({ kind: "new", key: "new", text });
      }
    }
    return result;
  }, [kind, query, value, inventory, labelNames, byName]);

  const add = (raw: string) => {
    if (value.includes(raw)) return;
    onChange([...value, raw]);
  };

  const select = (option: MatcherOption) => {
    if (option.kind === "label") {
      add(serializePattern({ mode: "exact", value: option.item.name }));
    } else if (option.kind === "contains") {
      add(serializePattern({ mode: "contains", value: option.text }));
    } else {
      add(serializePattern({ mode: "exact", value: option.text }));
    }
    setQuery("");
    setHighlighted(0);
  };

  const addTitleWords = () => {
    const text = query.trim();
    if (!text) return;
    add(serializePattern({ mode: "contains", value: text }));
    setQuery("");
  };

  const addAdvanced = () => {
    const text = advancedText.trim();
    if (!text) return;
    add(serializePattern({ mode: "regex", value: text }));
    setAdvancedText("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (kind === "title") {
      if (e.key === "Enter") {
        e.preventDefault();
        addTitleWords();
      } else if (e.key === "Backspace" && !query && value.length > 0) {
        onChange(value.slice(0, -1));
      }
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      if (options.length > 0) setHighlighted((prev) => (prev + 1) % options.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setOpen(true);
      if (options.length > 0) {
        setHighlighted((prev) => (prev - 1 + options.length) % options.length);
      }
    } else if (e.key === "Enter") {
      if (open && options.length > 0) {
        e.preventDefault();
        select(options[Math.min(highlighted, options.length - 1)]);
      }
    } else if (e.key === "Escape") {
      if (open) {
        e.preventDefault();
        e.stopPropagation();
        setOpen(false);
      }
    } else if (e.key === "Backspace" && !query && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  };

  const listId = `${id}-list`;
  const showList = kind === "label" && open && options.length > 0 && !disabled;
  const activeOptionId = showList
    ? `${id}-opt-${Math.min(highlighted, options.length - 1)}`
    : undefined;
  const problemEntries = Object.entries(problems ?? {});

  return (
    <div className="settings-matcher">
      <div className="settings-matcher-field">
        {value.map((raw, i) => {
          const problem = problems?.[i];
          const style = chipStyle(raw, byName);
          const unmatched = matchCounts?.[raw] === 0;
          return (
            <span
              key={`${raw}:${i}`}
              className={`settings-chip${style ? " styled" : ""}${problem ? " error" : ""}${unmatched ? " unmatched" : ""}`}
              style={style}
              title={unmatched ? "No issue matches this right now" : undefined}
            >
              <span className="settings-chip-text">{describePattern(raw)}</span>
              {unmatched && (
                <span className="settings-visually-hidden">No issue matches this right now</span>
              )}
              {!disabled && (
                <button
                  type="button"
                  className="settings-chip-remove"
                  aria-label={`Remove ${describePattern(raw)}`}
                  aria-describedby={problem ? `${id}-problem-${i}` : undefined}
                  onClick={() => onChange(value.filter((_, idx) => idx !== i))}
                >
                  <X size={11} />
                </button>
              )}
            </span>
          );
        })}
        <div className="settings-matcher-combo">
          <input
            id={id}
            type="text"
            className="settings-matcher-input"
            role={kind === "label" ? "combobox" : undefined}
            aria-expanded={kind === "label" ? showList : undefined}
            aria-controls={kind === "label" ? listId : undefined}
            aria-activedescendant={activeOptionId}
            aria-autocomplete={kind === "label" ? "list" : undefined}
            aria-label={ariaLabel}
            disabled={disabled}
            value={query}
            placeholder={kind === "label" ? "Find a label..." : "Add words from the title..."}
            onFocus={() => setOpen(true)}
            onBlur={() => setOpen(false)}
            onChange={(e) => {
              setQuery(e.target.value);
              setHighlighted(0);
              setOpen(true);
            }}
            onKeyDown={handleKeyDown}
          />
          {showList && (
            <div className="scope-dropdown settings-matcher-dropdown" role="listbox" id={listId} aria-label={ariaLabel}>
              {options.map((option, idx) => {
                const active = idx === Math.min(highlighted, options.length - 1);
                return (
                  <button
                    key={option.key}
                    id={`${id}-opt-${idx}`}
                    type="button"
                    role="option"
                    tabIndex={-1}
                    aria-selected={active}
                    className={`scope-option${active ? " active" : ""}`}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      select(option);
                    }}
                    onMouseEnter={() => setHighlighted(idx)}
                  >
                    {option.kind === "label" && (
                      <>
                        <span className="settings-option-name">
                          <span
                            className="settings-swatch"
                            style={option.item.color ? { background: option.item.color } : undefined}
                            aria-hidden="true"
                          />
                          <span className="scope-option-label">{option.item.name}</span>
                        </span>
                        <span className="scope-option-count">
                          used by {option.item.count} {option.item.count === 1 ? "issue" : "issues"}
                        </span>
                      </>
                    )}
                    {option.kind === "contains" && (
                      <span className="scope-option-label">
                        Any label containing "{option.text}" (matches {option.matches}{" "}
                        {option.matches === 1 ? "label" : "labels"})
                      </span>
                    )}
                    {option.kind === "new" && (
                      <span className="scope-option-label">
                        Use "{option.text}" as a new label name
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>
        {kind === "title" && !disabled && (
          <button
            type="button"
            className="pulse-btn-secondary settings-btn-small"
            disabled={!query.trim()}
            onClick={addTitleWords}
          >
            Add
          </button>
        )}
      </div>

      {value.some((raw) => matchCounts?.[raw] === 0) && (
        <p className="settings-hint">Entries outlined in amber match no issue right now.</p>
      )}

      {problemEntries.map(([index, message]) => (
        <p key={index} id={`${id}-problem-${index}`} className="settings-error-text" role="alert">
          {message}
        </p>
      ))}

      {kind === "title" && (
        <p className="settings-hint">Upper and lower case matter: "bug" does not match "Bug".</p>
      )}

      {!disabled && (
        <details className="settings-advanced">
          <summary>Advanced</summary>
          <div className="settings-advanced-body">
            <div className="settings-inline-form">
              <input
                type="text"
                className="settings-input"
                aria-label={`${ariaLabel}: matches pattern`}
                value={advancedText}
                placeholder="matches pattern"
                onChange={(e) => setAdvancedText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    addAdvanced();
                  }
                }}
              />
              <button
                type="button"
                className="pulse-btn-secondary settings-btn-small"
                disabled={!advancedText.trim()}
                onClick={addAdvanced}
              >
                Add pattern
              </button>
            </div>
            <p className="settings-hint">
              Patterns are checked when you save. Use them only if picking labels is not enough.
            </p>
          </div>
        </details>
      )}
    </div>
  );
}
