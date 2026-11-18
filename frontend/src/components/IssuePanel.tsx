import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ChevronLeft, ChevronRight, KanbanSquare, Table2, X } from "lucide-react";
import { getBoardLanes } from "../lib/board";
import { applyFacets, buildFacetChips, withoutFacet } from "../lib/facets";
import type {
  ActiveChartId,
  GlobalFilters,
  IssueFacets,
  IssueItem,
  IssueViewMode,
  LabelStyle,
  OverviewLayout,
  ThemeMode,
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
  layout: OverviewLayout;
  activeChart: ActiveChartId;
  showFilters: boolean;
  laneHeaders: boolean;
  labelStyles: Record<string, LabelStyle>;
  palette: Record<string, string>;
  priorityOrder: string[];
  theme: ThemeMode;
  toolbarLeft?: ReactNode;
  onChangeFacets: (next: IssueFacets) => void;
  onRemoveSidebarFilter: (key: string) => void;
  onClearAll: () => void;
  onClearChartFilter: () => void;
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
  layout,
  activeChart,
  showFilters,
  laneHeaders,
  labelStyles,
  palette,
  priorityOrder,
  theme,
  toolbarLeft,
  onChangeFacets,
  onRemoveSidebarFilter,
  onClearAll,
  onClearChartFilter,
}: IssuePanelProps) {
  const [viewMode, setViewMode] = useState<IssueViewMode>("table");
  const [tableSize, setTableSize] = useState<TablePageSize>("fit");
  const [boardSize, setBoardSize] = useState<BoardPageSize>(10);
  const [pageIndex, setPageIndex] = useState(0);
  const [fitRows, setFitRows] = useState(14);
  const panelRef = useRef<HTMLElement | null>(null);
  const headRef = useRef<HTMLDivElement | null>(null);

  const filteredIssues = useMemo(() => applyFacets(issues, facets), [issues, facets]);

  const laneCountSource = useMemo(
    () => applyFacets(issues, withoutFacet(withoutFacet(facets, "stage"), "priority")),
    [issues, facets],
  );

  const chips = useMemo(
    () => buildFacetChips(facets, globalFilters, defaultStartDate, defaultEndDate),
    [facets, globalFilters, defaultStartDate, defaultEndDate],
  );

  // Compute responsive Fit row count from viewport height below the panel head
  useEffect(() => {
    const computeFit = () => {
      const headEl = headRef.current;
      if (headEl && panelRef.current) {
        panelRef.current.style.setProperty("--panel-head-h", `${headEl.offsetHeight}px`);
      }
      const rect = headEl?.getBoundingClientRect();
      const topUsed = rect ? Math.min(rect.bottom, window.innerHeight * 0.6) : 220;
      const available = Math.max(window.innerHeight - topUsed - 64, 185);
      const count = Math.max(5, Math.min(100, Math.floor(available / 37)));
      setFitRows(count);
    };

    computeFit();
    window.addEventListener("resize", computeFit);
    const el = headRef.current;
    let ro: ResizeObserver | null = null;
    if (el && typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(computeFit);
      ro.observe(el);
    }
    return () => {
      window.removeEventListener("resize", computeFit);
      ro?.disconnect();
    };
  }, [layout, viewMode, chips.length]);

  // Calculate total items to page (total rows in Table, tallest lane card count in Board)
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

  // Reset page index when filters or view change
  useEffect(() => {
    setPageIndex(0);
  }, [facets, globalFilters, viewMode, tableSize, boardSize]);

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

  return (
    <section ref={panelRef} className="issue-panel" aria-label="Issues">
      <div
        ref={headRef}
        className={`issue-panel-sticky-head ${layout === "analytics" ? "below-workflow" : ""}`}
      >
        <div className="issue-toolbar">
          {showFilters ? toolbarLeft : <div />}
          <div className="issue-toolbar-actions">
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
            <div className="pulse-segmented" role="group" aria-label="Issue display mode">
              <button
                type="button"
                aria-pressed={viewMode === "table"}
                onClick={() => setViewMode("table")}
              >
                <Table2 size={14} />
                <span>Table</span>
              </button>
              <button
                type="button"
                aria-pressed={viewMode === "board"}
                onClick={() => setViewMode("board")}
              >
                <KanbanSquare size={14} />
                <span>Board</span>
              </button>
            </div>
          </div>
        </div>

        <div className="issue-subbar">
          <div className="issue-chips">
            {showFilters &&
              chips.map((chip) => (
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
            {showFilters && chips.length > 0 && (
              <button type="button" className="clear-all-btn" onClick={onClearAll}>
                Clear all
              </button>
            )}
            {!showFilters && activeChart !== null && (
              <button
                type="button"
                className="filter-chip"
                onClick={onClearChartFilter}
                title="Clear active chart filter"
              >
                <span>Chart filter active</span>
                <X size={12} aria-hidden="true" />
              </button>
            )}
            <span className="issue-count-caption">
              {filteredIssues.length.toLocaleString()} issue
              {filteredIssues.length === 1 ? "" : "s"}
            </span>
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
                  <ChevronLeft size={15} />
                </button>
                <button
                  type="button"
                  className="pager-btn"
                  aria-label="Next page"
                  disabled={safePageIndex >= totalPages - 1}
                  onClick={() => setPageIndex((p) => Math.min(totalPages - 1, p + 1))}
                >
                  <ChevronRight size={15} />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

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
        />
      ) : (
        <IssueBoard
          issues={filteredIssues}
          laneCountSource={laneCountSource}
          overviewStages={overviewStages}
          laneHeaders={laneHeaders}
          facets={facets}
          palette={palette}
          priorityOrder={priorityOrder}
          theme={theme}
          pageStart={pageStart}
          pageSize={pageSize}
          onToggleLanePill={handleToggleLanePill}
        />
      )}
    </section>
  );
}
