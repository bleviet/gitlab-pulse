import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Calendar, Filter, Search, X } from "lucide-react";
import { resolvePresetDates } from "../lib/facets";
import {
  buildScopeSuggestions,
  type ScopeCombinedMatch,
  type ScopeDimension,
  type ScopeOptionMatch,
} from "../lib/scopeSearch";
import type { GlobalFilters, IssueItem, TimePreset } from "../lib/types";

interface ScopeBarProps {
  issues: IssueItem[];
  filters: GlobalFilters;
  options: { teams: string[]; contexts: string[]; milestones: string[] };
  minDate: string;
  maxDate: string;
  matchedCount: number;
  totalCount: number;
  onChangeFilters: (next: GlobalFilters) => void;
  onApplyIssueQuery: (query: string) => void;
}

type FlatScopeItem =
  | ScopeCombinedMatch
  | ScopeOptionMatch
  | { kind: "issue_search"; id: string; query: string };

const FIXED_PRESETS: Array<[Exclude<TimePreset, "custom">, string]> = [
  ["30d", "30d"],
  ["90d", "90d"],
  ["1y", "1y"],
  ["all", "All"],
];

const DIMENSION_LABELS: Record<ScopeDimension, string> = {
  team: "Team",
  context: "Context",
  milestone: "Milestone",
};

function formatCompactDay(isoDate: string): string {
  if (!isoDate) return "";
  const parsed = new Date(`${isoDate}T00:00:00Z`);
  if (Number.isNaN(parsed.getTime())) return isoDate;
  return parsed.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
}

function formatShortRange(start: string, end: string): string {
  if (start && end) return `${formatCompactDay(start)} - ${formatCompactDay(end)}`;
  if (start) return `From ${formatCompactDay(start)}`;
  if (end) return `Until ${formatCompactDay(end)}`;
  return "Custom";
}

export function ScopeBar({
  issues,
  filters,
  options,
  minDate,
  maxDate,
  matchedCount,
  totalCount,
  onChangeFilters,
  onApplyIssueQuery,
}: ScopeBarProps) {
  const [query, setQuery] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [dateOpen, setDateOpen] = useState(false);
  const [highlightedIdx, setHighlightedIdx] = useState(0);

  const containerRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!menuOpen && !dateOpen) return;
    const onPointerDown = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
        setDateOpen(false);
      }
    };
    const onKeyDown = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") {
        setMenuOpen(false);
        setDateOpen(false);
        inputRef.current?.blur();
      }
    };
    document.addEventListener("mousedown", onPointerDown);
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen, dateOpen]);

  const suggestions = useMemo(
    () => buildScopeSuggestions(issues, filters, options, query),
    [issues, filters, options, query],
  );

  const flatItems = useMemo<FlatScopeItem[]>(() => {
    const items: FlatScopeItem[] = [
      ...suggestions.combined,
      ...suggestions.teams,
      ...suggestions.contexts,
      ...suggestions.milestones,
    ];
    const trimmed = query.trim();
    if (trimmed && items.length === 0) {
      items.push({ kind: "issue_search", id: "issue_search", query: trimmed });
    }
    return items;
  }, [suggestions, query]);

  useEffect(() => {
    setHighlightedIdx(0);
  }, [query, flatItems.length]);

  const activeTokens = useMemo(() => {
    const tokens: Array<{ dimension: ScopeDimension; value: string }> = [];
    if (filters.team !== "All") tokens.push({ dimension: "team", value: filters.team });
    if (filters.context !== "All") tokens.push({ dimension: "context", value: filters.context });
    if (filters.milestone !== "All") {
      tokens.push({ dimension: "milestone", value: filters.milestone });
    }
    return tokens;
  }, [filters.team, filters.context, filters.milestone]);

  const applyPreset = (preset: TimePreset) => {
    const dates = resolvePresetDates(preset, minDate, maxDate, filters.startDate, filters.endDate);
    onChangeFilters({
      ...filters,
      preset,
      startDate: dates.startDate,
      endDate: dates.endDate,
    });
    if (preset !== "custom") {
      setDateOpen(false);
    }
  };

  const handleSelectItem = (item: FlatScopeItem) => {
    if (item.kind === "combined") {
      onChangeFilters({ ...filters, ...item.patch });
      setQuery("");
      setMenuOpen(false);
      return;
    }
    if (item.kind === "issue_search") {
      onApplyIssueQuery(item.query);
      setQuery("");
      setMenuOpen(false);
      inputRef.current?.blur();
      return;
    }

    const nextFilters = { ...filters, [item.dimension]: item.value };
    onChangeFilters(nextFilters);
    setQuery("");

    const hasRemaining =
      (options.teams.length > 1 && nextFilters.team === "All") ||
      (options.contexts.length > 0 && nextFilters.context === "All") ||
      (options.milestones.length > 0 && nextFilters.milestone === "All");

    if (hasRemaining) {
      setMenuOpen(true);
      inputRef.current?.focus();
    } else {
      setMenuOpen(false);
    }
  };

  const handleClearScopes = () => {
    onChangeFilters({
      ...filters,
      team: "All",
      context: "All",
      milestone: "All",
    });
    setQuery("");
    inputRef.current?.focus();
  };

  const handleInputKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!menuOpen) setMenuOpen(true);
      if (flatItems.length > 0) {
        setHighlightedIdx((prev) => (prev + 1) % flatItems.length);
      }
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!menuOpen) setMenuOpen(true);
      if (flatItems.length > 0) {
        setHighlightedIdx((prev) => (prev - 1 + flatItems.length) % flatItems.length);
      }
      return;
    }
    if (e.key === "Enter" && menuOpen && flatItems.length > 0) {
      e.preventDefault();
      const target = flatItems[Math.min(highlightedIdx, flatItems.length - 1)];
      if (target) handleSelectItem(target);
      return;
    }
    if (e.key === "Backspace" && !query && activeTokens.length > 0) {
      const last = activeTokens[activeTokens.length - 1];
      onChangeFilters({ ...filters, [last.dimension]: "All" });
      return;
    }
    if (e.key === "Escape") {
      setMenuOpen(false);
      inputRef.current?.blur();
    }
  };

  const itemIndexById = new Map<string, number>();
  flatItems.forEach((item, idx) => itemIndexById.set(item.id, idx));

  const renderSingleSection = (title: string, items: ScopeOptionMatch[]) => {
    if (items.length === 0) return null;
    return (
      <div className="scope-group">
        <div className="scope-group-title">{title}</div>
        {items.map((item) => {
          const idx = itemIndexById.get(item.id) ?? -1;
          const isActive = idx === highlightedIdx;
          return (
            <button
              key={item.id}
              type="button"
              role="option"
              aria-selected={isActive}
              className={`scope-option${isActive ? " active" : ""}`}
              onMouseDown={(e) => {
                e.preventDefault();
                handleSelectItem(item);
              }}
              onMouseEnter={() => {
                if (idx >= 0) setHighlightedIdx(idx);
              }}
            >
              <span className="scope-option-label">{item.value}</span>
              <span className="scope-option-count">{item.count}</span>
            </button>
          );
        })}
      </div>
    );
  };

  const hasTokensOrQuery = activeTokens.length > 0 || query.length > 0;
  const fallbackSearchItem = flatItems.find(
    (item): item is { kind: "issue_search"; id: string; query: string } =>
      item.kind === "issue_search",
  );

  return (
    <div ref={containerRef} className="scope-root">
      <div className="scope-inline" role="group" aria-label="Workspace scope filters">
        <div className="scope-combobox-wrap">
          <div
            className="scope-combobox"
            onClick={() => {
              setDateOpen(false);
              setMenuOpen(true);
              inputRef.current?.focus();
            }}
          >
            <Filter size={13} className="scope-combobox-icon" aria-hidden="true" />
            {activeTokens.map((token) => (
              <span
                key={token.dimension}
                className="scope-token"
                title={`${DIMENSION_LABELS[token.dimension]}: ${token.value}`}
              >
                <span className="scope-token-text">{token.value}</span>
                <button
                  type="button"
                  className="scope-token-remove"
                  aria-label={`Remove ${DIMENSION_LABELS[token.dimension]} ${token.value}`}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={(e) => {
                    e.stopPropagation();
                    onChangeFilters({ ...filters, [token.dimension]: "All" });
                  }}
                >
                  <X size={11} />
                </button>
              </span>
            ))}
            <input
              ref={inputRef}
              type="text"
              role="combobox"
              aria-expanded={menuOpen}
              aria-autocomplete="list"
              aria-label="Filter scope by context, milestone, or team"
              value={query}
              placeholder={
                activeTokens.length > 0
                  ? "Add scope..."
                  : options.teams.length > 1
                    ? "Scope: context, milestone, team..."
                    : "Scope: context, milestone..."
              }
              onFocus={() => {
                setDateOpen(false);
                setMenuOpen(true);
              }}
              onChange={(e) => {
                setQuery(e.target.value);
                if (!menuOpen) setMenuOpen(true);
              }}
              onKeyDown={handleInputKeyDown}
            />
            {hasTokensOrQuery && (
              <button
                type="button"
                className="scope-clear-btn"
                aria-label="Clear scope selection"
                onMouseDown={(e) => e.preventDefault()}
                onClick={(e) => {
                  e.stopPropagation();
                  handleClearScopes();
                }}
              >
                <X size={12} />
              </button>
            )}
          </div>

          {menuOpen && (
            <div className="scope-dropdown" role="listbox" aria-label="Scope suggestions">
              {suggestions.combined.length > 0 && (
                <div className="scope-group">
                  <div className="scope-group-title">Quick apply</div>
                  {suggestions.combined.map((item) => {
                    const idx = itemIndexById.get(item.id) ?? -1;
                    const isActive = idx === highlightedIdx;
                    return (
                      <button
                        key={item.id}
                        type="button"
                        role="option"
                        aria-selected={isActive}
                        className={`scope-option${isActive ? " active" : ""}`}
                        onMouseDown={(e) => {
                          e.preventDefault();
                          handleSelectItem(item);
                        }}
                        onMouseEnter={() => {
                          if (idx >= 0) setHighlightedIdx(idx);
                        }}
                      >
                        <span className="scope-combo-labels">
                          {item.labels.map((lbl, i) => (
                            <span key={`${lbl.dimension}:${lbl.value}`} className="scope-combo-part">
                              {i > 0 && <span className="scope-combo-plus">+</span>}
                              <span className="scope-combo-pill">{lbl.value}</span>
                            </span>
                          ))}
                        </span>
                        <span className="scope-option-count">{item.count}</span>
                      </button>
                    );
                  })}
                </div>
              )}

              {renderSingleSection("Teams", suggestions.teams)}
              {renderSingleSection("Contexts", suggestions.contexts)}
              {renderSingleSection("Milestones", suggestions.milestones)}

              {fallbackSearchItem && (
                <div className="scope-group">
                  <button
                    type="button"
                    role="option"
                    aria-selected={highlightedIdx === 0}
                    className={`scope-option${highlightedIdx === 0 ? " active" : ""}`}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      handleSelectItem(fallbackSearchItem);
                    }}
                  >
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.4rem",
                        minWidth: 0,
                      }}
                    >
                      <Search size={13} color="var(--accent)" />
                      <span>
                        Search issues for <strong>{fallbackSearchItem.query}</strong>
                      </span>
                    </span>
                  </button>
                </div>
              )}

              {!fallbackSearchItem &&
                suggestions.combined.length === 0 &&
                suggestions.teams.length === 0 &&
                suggestions.contexts.length === 0 &&
                suggestions.milestones.length === 0 && (
                  <div className="scope-empty">All scope options selected.</div>
                )}
            </div>
          )}
        </div>

        <div className="pulse-segmented" role="group" aria-label="Time range presets">
          {FIXED_PRESETS.map(([preset, label]) => (
            <button
              key={preset}
              type="button"
              aria-pressed={filters.preset === preset}
              onClick={() => applyPreset(preset)}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="scope-popover-anchor">
          <button
            type="button"
            className="pulse-icon-btn pulse-toggle-btn"
            aria-pressed={filters.preset === "custom"}
            aria-expanded={dateOpen}
            aria-label="Custom date range"
            title="Custom date range"
            onClick={() => {
              setMenuOpen(false);
              setDateOpen((prev) => !prev);
            }}
          >
            <Calendar size={14} />
            {filters.preset === "custom" && (
              <span style={{ fontSize: "0.75rem", fontFamily: "var(--font-mono)" }}>
                {formatShortRange(filters.startDate, filters.endDate)}
              </span>
            )}
          </button>

          {dateOpen && (
            <div
              className="scope-popover scope-popover-date"
              role="dialog"
              aria-label="Custom date range"
            >
              <div className="scope-popover-head">
                <span className="pulse-panel-title">Custom Date Range</span>
                <span className="issue-count-caption">
                  {matchedCount} / {totalCount}
                </span>
                <button
                  type="button"
                  className="pulse-icon-btn"
                  style={{ width: "26px", height: "26px", padding: 0 }}
                  aria-label="Close custom date range"
                  onClick={() => setDateOpen(false)}
                >
                  <X size={13} />
                </button>
              </div>

              <div className="scope-date-grid">
                <div className="scope-field">
                  <label htmlFor="scope-desktop-start">Start</label>
                  <input
                    id="scope-desktop-start"
                    type="date"
                    value={filters.startDate}
                    min={minDate || undefined}
                    max={filters.endDate || maxDate || undefined}
                    onChange={(e) =>
                      onChangeFilters({
                        ...filters,
                        startDate: e.target.value,
                        preset: "custom",
                      })
                    }
                  />
                </div>
                <div className="scope-field">
                  <label htmlFor="scope-desktop-end">End</label>
                  <input
                    id="scope-desktop-end"
                    type="date"
                    value={filters.endDate}
                    min={filters.startDate || minDate || undefined}
                    max={maxDate || undefined}
                    onChange={(e) =>
                      onChangeFilters({
                        ...filters,
                        endDate: e.target.value,
                        preset: "custom",
                      })
                    }
                  />
                </div>
              </div>

              {filters.preset !== "all" && (
                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <button
                    type="button"
                    className="scope-reset-link"
                    onClick={() => applyPreset("all")}
                  >
                    Reset to All Time
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
