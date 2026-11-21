import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  KanbanSquare,
  Pencil,
  RotateCcw,
  Table2,
  X,
} from "lucide-react";
import { getBoardLanes } from "../lib/board";
import { applyFacets, buildFacetChips, withoutFacet } from "../lib/facets";
import {
  createEmptyStandupState,
  filterIssuesByCoverage,
  markIssueOpened,
  nextCoveredFilterMode,
  parseStandupState,
  STANDUP_STORAGE_KEY,
  toggleIssueCovered,
  type CoveredFilterMode,
  type StandupState,
} from "../lib/standup";
import type {
  GlobalFilters,
  IssueFacets,
  IssueItem,
  IssueViewMode,
  LabelStyle,
  ThemeMode,
  ValueMode,
} from "../lib/types";
import { IssueBoard } from "./IssueBoard";
import { IssueSearchInput } from "./IssueSearchInput";
import { IssueTable } from "./IssueTable";

interface IssuePanelProps {
  issues: IssueItem[];
  overviewStages: string[];
  facets: IssueFacets;
  globalFilters: GlobalFilters;
  defaultStartDate: string;
  defaultEndDate: string;
  chartsVisible: boolean;
  viewMode: IssueViewMode;
  labelStyles: Record<string, LabelStyle>;
  palette: Record<string, string>;
  priorityOrder: string[];
  theme: ThemeMode;
  valueMode: ValueMode;
  summaryBar?: ReactNode;
  onChangeViewMode: (mode: IssueViewMode) => void;
  onChangeFacets: (next: IssueFacets) => void;
  onRemoveSidebarFilter: (key: string) => void;
  onClearAll: () => void;
  editMode?: boolean;
  stagesPopoverOpen?: boolean;
  onEditStages?: (anchor: HTMLElement | null) => void;
}

type TablePageSize = "fit" | 10 | 20 | 30;
type BoardPageSize = 10 | 20 | 30;

export function IssuePanel({
  issues,
  overviewStages,
  facets,
  globalFilters,
  defaultStartDate,
  defaultEndDate,
  chartsVisible,
  viewMode,
  labelStyles,
  palette,
  priorityOrder,
  theme,
  valueMode,
  summaryBar,
  onChangeViewMode,
  onChangeFacets,
  onRemoveSidebarFilter,
  onClearAll,
  editMode = false,
  stagesPopoverOpen = false,
  onEditStages,
}: IssuePanelProps) {
  const [tableSize, setTableSize] = useState<TablePageSize>("fit");
  const [boardSize, setBoardSize] = useState<BoardPageSize>(10);
  const [pageIndex, setPageIndex] = useState(0);
  const [fitRows, setFitRows] = useState(16);
  const [standupState, setStandupState] = useState<StandupState>(() => {
    try {
      return parseStandupState(localStorage.getItem(STANDUP_STORAGE_KEY));
    } catch {
      return createEmptyStandupState();
    }
  });
  const [coveredFilterMode, setCoveredFilterMode] = useState<CoveredFilterMode>("all");
  const panelRef = useRef<HTMLElement | null>(null);
  const headRef = useRef<HTMLDivElement | null>(null);
  const bodyRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(STANDUP_STORAGE_KEY, JSON.stringify(standupState));
    } catch {
      // ignore storage restriction
    }
  }, [standupState]);

  const coveredSet = useMemo(
    () => new Set(standupState.coveredIds),
    [standupState.coveredIds],
  );

  const facetFilteredIssues = useMemo(() => applyFacets(issues, facets), [issues, facets]);

  const coveredInViewCount = useMemo(
    () => facetFilteredIssues.filter((issue) => coveredSet.has(issue.id)).length,
    [facetFilteredIssues, coveredSet],
  );

  const totalCoveredToday = standupState.coveredIds.length;
  const effectiveCoveredFilter: CoveredFilterMode =
    totalCoveredToday === 0 ? "all" : coveredFilterMode;

  const filteredIssues = useMemo(
    () => filterIssuesByCoverage(facetFilteredIssues, coveredSet, effectiveCoveredFilter),
    [facetFilteredIssues, coveredSet, effectiveCoveredFilter],
  );

  const handleOpenIssue = useCallback((issueId: number) => {
    setStandupState((prev) => markIssueOpened(prev, issueId));
  }, []);

  const handleToggleCovered = useCallback((issueId: number) => {
    setStandupState((prev) => toggleIssueCovered(prev, issueId));
  }, []);

  const handleResetStandup = useCallback(() => {
    setStandupState(createEmptyStandupState());
    setCoveredFilterMode("all");
  }, []);

  const laneCountSource = useMemo(
    () =>
      filterIssuesByCoverage(
        applyFacets(issues, withoutFacet(withoutFacet(facets, "stage"), "priority")),
        coveredSet,
        effectiveCoveredFilter,
      ),
    [issues, facets, coveredSet, effectiveCoveredFilter],
  );

  const chips = useMemo(
    () => buildFacetChips(facets, globalFilters, defaultStartDate, defaultEndDate),
    [facets, globalFilters, defaultStartDate, defaultEndDate],
  );

  useEffect(() => {
    const computeFit = () => {
      const headEl = headRef.current;
      if (headEl && panelRef.current) {
        panelRef.current.style.setProperty("--panel-head-h", `${headEl.offsetHeight}px`);
      }

      if (bodyRef.current && window.innerWidth >= 768) {
        const bodyHeight = bodyRef.current.clientHeight;
        if (bodyHeight > 0) {
          const count = Math.max(5, Math.min(100, Math.floor((bodyHeight - 33) / 31)));
          setFitRows(count);
          return;
        }
      }

      const rect = headEl?.getBoundingClientRect();
      const topUsed = rect ? Math.min(rect.bottom, window.innerHeight * 0.6) : 200;
      const available = Math.max(window.innerHeight - topUsed - 60, 180);
      const count = Math.max(5, Math.min(100, Math.floor(available / 34)));
      setFitRows(count);
    };

    computeFit();
    window.addEventListener("resize", computeFit);
    let ro: ResizeObserver | null = null;
    if (typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(computeFit);
      if (headRef.current) ro.observe(headRef.current);
      if (bodyRef.current) ro.observe(bodyRef.current);
    }
    return () => {
      window.removeEventListener("resize", computeFit);
      ro?.disconnect();
    };
  }, [chartsVisible, viewMode, chips.length]);

  const boardLanes = useMemo(
    () => getBoardLanes(overviewStages, filteredIssues),
    [overviewStages, filteredIssues],
  );

  const boardMaxLaneCount = useMemo(() => {
    if (viewMode !== "board" || boardLanes.length === 0) return 0;
    const counts = new Map<string, number>();
    for (const issue of filteredIssues) {
      counts.set(issue.stage, (counts.get(issue.stage) ?? 0) + 1);
    }
    return Math.max(0, ...boardLanes.map((lane) => counts.get(lane) ?? 0));
  }, [viewMode, boardLanes, filteredIssues]);

  const pageSize = viewMode === "table" ? (tableSize === "fit" ? fitRows : tableSize) : boardSize;
  const pageTotalItems = viewMode === "table" ? filteredIssues.length : boardMaxLaneCount;
  const totalPages = Math.max(1, Math.ceil(pageTotalItems / pageSize));
  const safePageIndex = Math.min(pageIndex, totalPages - 1);
  const pageStart = safePageIndex * pageSize;
  const pageStop = Math.min(pageStart + pageSize, pageTotalItems);

  useEffect(() => {
    setPageIndex(0);
  }, [facets, globalFilters, viewMode, tableSize, boardSize, effectiveCoveredFilter]);

  const handleToggleLanePill = (stage: string, priority: string) => {
    const isSame =
      facets.stage === stage &&
      facets.priority?.toLowerCase() === priority.toLowerCase();
    if (isSame) {
      onChangeFacets(withoutFacet(withoutFacet(facets, "stage"), "priority"));
    } else {
      onChangeFacets({
        ...facets,
        state: facets.state ?? "opened",
        stage,
        priority,
      });
    }
  };

  const remainingInViewCount = Math.max(0, facetFilteredIssues.length - coveredInViewCount);
  const standupPillLabel =
    effectiveCoveredFilter === "remaining"
      ? `Remaining (${remainingInViewCount})`
      : effectiveCoveredFilter === "covered"
        ? `Covered only (${coveredInViewCount})`
        : `${coveredInViewCount}/${facetFilteredIssues.length} covered`;

  return (
    <section ref={panelRef} className="issue-panel" aria-label="Issues">
      <div ref={headRef} className="issue-panel-sticky-head">
        {!chartsVisible && summaryBar && <div className="issue-summary-strip">{summaryBar}</div>}

        <div className="issue-toolbar analytics-single-bar">
          <div className="analytics-bar-left">
            <span className="issue-count-caption">
              {filteredIssues.length.toLocaleString()} issue
              {filteredIssues.length === 1 ? "" : "s"}
            </span>
            {totalCoveredToday > 0 && (
              <span className="standup-toolbar-group" role="group" aria-label="Covered today">
                <button
                  type="button"
                  className={`standup-filter-pill ${effectiveCoveredFilter !== "all" ? "active" : ""}`}
                  aria-pressed={effectiveCoveredFilter !== "all"}
                  title="Click to cycle filter: All -> Remaining -> Covered today"
                  onClick={() => setCoveredFilterMode((prev) => nextCoveredFilterMode(prev))}
                >
                  <CheckCircle2 size={13} aria-hidden="true" />
                  <span>{standupPillLabel}</span>
                </button>
                <button
                  type="button"
                  className="standup-reset-btn"
                  aria-label="Reset today's covered issues"
                  title="Reset today's covered issues"
                  onClick={handleResetStandup}
                >
                  <RotateCcw size={12} aria-hidden="true" />
                </button>
              </span>
            )}
            {chips.map((chip) => (
              <button
                key={`${chip.kind}_${chip.key}`}
                type="button"
                className="filter-chip"
                title="Remove filter"
                onClick={() => {
                  if (chip.kind === "facet") {
                    onChangeFacets(withoutFacet(facets, chip.key as keyof IssueFacets));
                  } else {
                    onRemoveSidebarFilter(chip.key);
                  }
                }}
              >
                <span>{chip.label}</span>
                <X size={12} aria-hidden="true" />
              </button>
            ))}
            {(chips.length > 0 || effectiveCoveredFilter !== "all") && (
              <button
                type="button"
                className="clear-all-btn"
                onClick={() => {
                  setCoveredFilterMode("all");
                  onClearAll();
                }}
              >
                Clear all
              </button>
            )}
          </div>

          <div className="analytics-bar-right">
            <IssueSearchInput
              value={facets.query ?? ""}
              onChange={(nextQuery) => {
                if (nextQuery) {
                  onChangeFacets({ ...facets, query: nextQuery });
                } else {
                  onChangeFacets(withoutFacet(facets, "query"));
                }
              }}
            />

            {editMode && viewMode === "board" && onEditStages && (
              <button
                type="button"
                data-rule-trigger="stages"
                className={`panel-edit-btn${stagesPopoverOpen ? " active" : ""}`}
                aria-expanded={stagesPopoverOpen}
                onClick={(e) => onEditStages(e.currentTarget)}
              >
                <Pencil size={11} aria-hidden="true" />
                <span>Stages</span>
              </button>
            )}

            <div className="pulse-segmented" role="group" aria-label="Issue display mode">
              <button
                type="button"
                aria-pressed={viewMode === "table"}
                onClick={() => onChangeViewMode("table")}
              >
                <Table2 size={14} />
                <span>Table</span>
              </button>
              <button
                type="button"
                aria-pressed={viewMode === "board"}
                onClick={() => onChangeViewMode("board")}
              >
                <KanbanSquare size={14} />
                <span>Board</span>
              </button>
            </div>

            <div className="issue-pager">
              {viewMode === "table" ? (
                <div className="pulse-segmented" role="group" aria-label="Rows per page">
                  {(["fit", 10, 20, 30] as const).map((opt) => (
                    <button
                      key={String(opt)}
                      type="button"
                      aria-pressed={tableSize === opt}
                      onClick={() => setTableSize(opt)}
                    >
                      {opt === "fit" ? "Fit" : opt}
                    </button>
                  ))}
                </div>
              ) : (
                <div className="pulse-segmented" role="group" aria-label="Cards per lane">
                  {([10, 20, 30] as const).map((opt) => (
                    <button
                      key={opt}
                      type="button"
                      aria-pressed={boardSize === opt}
                      onClick={() => setBoardSize(opt)}
                    >
                      {opt}
                    </button>
                  ))}
                </div>
              )}

              <span className="issue-count-caption">
                {viewMode === "table"
                  ? pageTotalItems === 0
                    ? "0 of 0"
                    : `${pageStart + 1}–${pageStop} of ${pageTotalItems}`
                  : `Page ${safePageIndex + 1} of ${totalPages}`}
              </span>

              {totalPages > 1 && (
                <div style={{ display: "inline-flex", gap: "0.25rem" }}>
                  <button
                    type="button"
                    className="pager-btn"
                    aria-label="Previous page"
                    disabled={safePageIndex === 0}
                    onClick={() => setPageIndex((p) => Math.max(0, p - 1))}
                  >
                    <ChevronLeft size={14} />
                  </button>
                  <button
                    type="button"
                    className="pager-btn"
                    aria-label="Next page"
                    disabled={safePageIndex >= totalPages - 1}
                    onClick={() => setPageIndex((p) => Math.min(totalPages - 1, p + 1))}
                  >
                    <ChevronRight size={14} />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <div ref={bodyRef} className="issue-panel-body">
        {viewMode === "table" ? (
          <IssueTable
            issues={filteredIssues}
            facets={facets}
            labelStyles={labelStyles}
            palette={palette}
            priorityOrder={priorityOrder}
            theme={theme}
            pageStart={pageStart}
            pageStop={pageStop}
            coveredIds={coveredSet}
            activeIssueId={standupState.activeId}
            onOpenIssue={handleOpenIssue}
            onToggleCovered={handleToggleCovered}
          />
        ) : (
          <IssueBoard
            issues={filteredIssues}
            laneCountSource={laneCountSource}
            overviewStages={overviewStages}
            laneHeaders
            facets={facets}
            palette={palette}
            priorityOrder={priorityOrder}
            theme={theme}
            valueMode={valueMode}
            pageStart={pageStart}
            pageSize={pageSize}
            coveredIds={coveredSet}
            activeIssueId={standupState.activeId}
            onToggleLanePill={handleToggleLanePill}
            onOpenIssue={handleOpenIssue}
            onToggleCovered={handleToggleCovered}
          />
        )}
      </div>
    </section>
  );
}
