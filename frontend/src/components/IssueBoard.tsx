import { useMemo, useRef } from "react";
import { Check, ListTree } from "lucide-react";
import {
  computeLanePriorityCounts,
  getBoardLanes,
  getChildTaskCount,
  sortIssuesDefault,
} from "../lib/board";
import { getPriorityColor, hexWithAlpha } from "../lib/colors";
import { formatShare } from "../lib/analytics";
import type { IssueFacets, IssueItem, ThemeMode, ValueMode } from "../lib/types";

interface IssueBoardProps {
  issues: IssueItem[];
  laneCountSource: IssueItem[];
  overviewStages: string[];
  laneHeaders: boolean;
  facets: IssueFacets;
  palette: Record<string, string>;
  priorityOrder: string[];
  theme: ThemeMode;
  valueMode: ValueMode;
  pageStart: number;
  pageSize: number;
  coveredIds: ReadonlySet<number>;
  activeIssueId: number | null;
  onToggleLanePill: (stage: string, priority: string) => void;
  onOpenIssue: (issueId: number) => void;
  onToggleCovered: (issueId: number) => void;
}

export function IssueBoard({
  issues,
  laneCountSource,
  overviewStages,
  laneHeaders,
  facets,
  palette,
  priorityOrder,
  theme,
  valueMode,
  pageStart,
  pageSize,
  coveredIds,
  activeIssueId,
  onToggleLanePill,
  onOpenIssue,
  onToggleCovered,
}: IssueBoardProps) {
  const headScrollRef = useRef<HTMLDivElement | null>(null);
  const bodyScrollRef = useRef<HTMLDivElement | null>(null);

  const lanes = useMemo(
    () => getBoardLanes(overviewStages, issues),
    [overviewStages, issues],
  );

  const priorityMixByStage = useMemo(
    () => computeLanePriorityCounts(laneCountSource, palette, priorityOrder, theme),
    [laneCountSource, palette, priorityOrder, theme],
  );

  const cardsByStage = useMemo(() => {
    const sorted = sortIssuesDefault(issues);
    const map = new Map<string, IssueItem[]>();
    for (const lane of lanes) {
      map.set(lane, []);
    }
    for (const issue of sorted) {
      const bucket = map.get(issue.stage);
      if (bucket) {
        bucket.push(issue);
      }
    }
    return map;
  }, [issues, lanes]);

  if (lanes.length === 0) {
    return (
      <div style={{ padding: "1.5rem", textAlign: "center", color: "var(--muted)" }}>
        No issues to display.
      </div>
    );
  }

  const gridTemplateColumns = `repeat(${lanes.length}, minmax(15rem, 1fr))`;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.45rem" }}>
      {laneHeaders && (
        <div ref={headScrollRef} className="board-scroll-sync">
          <div className="board-grid" style={{ gridTemplateColumns }}>
            {lanes.map((stage) => {
              const allCards = cardsByStage.get(stage) ?? [];
              const mix = priorityMixByStage[stage] ?? [];
              const mixTotal = mix.reduce((acc, item) => acc + item.count, 0);
              const isHighlighted = facets.stage === stage;

              return (
                <div
                  key={stage}
                  className={`lane-head-card ${isHighlighted ? "highlighted" : ""}`}
                >
                  <div className="lane-head-title">
                    <span>{stage}</span>
                    <small>{allCards.length}</small>
                  </div>
                  <div className="lane-pbar" aria-hidden="true">
                    {mixTotal > 0 &&
                      mix.map((entry) => (
                        <span
                          key={entry.priority}
                          style={{
                            width: `${(entry.count / mixTotal) * 100}%`,
                            backgroundColor: entry.color,
                            minWidth: "3px",
                          }}
                        />
                      ))}
                  </div>
                  <div className="lane-pills">
                    {mix.map((entry) => {
                      const active =
                        facets.stage === stage &&
                        facets.priority?.toLowerCase() === entry.priority.toLowerCase();
                      return (
                        <button
                          key={entry.priority}
                          type="button"
                          className="lane-prio-pill"
                          aria-pressed={active}
                          onClick={() => onToggleLanePill(stage, entry.priority)}
                        >
                          <span
                            className="prio-dot"
                            style={{ width: 6, height: 6, background: entry.color }}
                            aria-hidden="true"
                          />
                          <span>{entry.priority}</span>
                          <strong style={{ fontFamily: "var(--font-mono)" }}>
                            {valueMode === "percent" ? formatShare(entry.count, mixTotal) : entry.count}
                          </strong>
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div
        ref={bodyScrollRef}
        className="board-lanes-scroll"
        onScroll={() => {
          if (headScrollRef.current && bodyScrollRef.current) {
            headScrollRef.current.scrollLeft = bodyScrollRef.current.scrollLeft;
          }
        }}
      >
        <div className="board-grid" style={{ gridTemplateColumns }}>
          {lanes.map((stage) => {
            const allCards = cardsByStage.get(stage) ?? [];
            const visibleCards = allCards.slice(pageStart, pageStart + pageSize);
            const remaining = Math.max(0, allCards.length - pageStart - visibleCards.length);
            const isHighlighted = facets.stage === stage;

            return (
              <div
                key={stage}
                className={`board-lane ${isHighlighted ? "highlighted" : ""}`}
              >
                {visibleCards.length === 0 ? (
                  <div
                    style={{
                      gridColumn: "1 / -1",
                      color: "var(--muted)",
                      fontSize: "0.78rem",
                      padding: "0.4rem 0.25rem",
                    }}
                  >
                    {allCards.length === 0 ? "No issues" : "No more issues"}
                  </div>
                ) : (
                  visibleCards.map((card) => {
                    const prio = card.priority || "Unset";
                    const prioColor = getPriorityColor(prio, palette, priorityOrder, theme);
                    const isCovered = coveredIds.has(card.id);
                    const isActive = activeIssueId === card.id;
                    const cardClass = [
                      "board-card",
                      isCovered ? "board-card-covered" : "",
                      isActive ? "board-card-active" : "",
                    ]
                      .filter(Boolean)
                      .join(" ");
                    return (
                      <article
                        key={card.id}
                        className={cardClass}
                        style={{ ["--card-prio-color" as string]: prioColor }}
                      >
                        <div className="board-card-head">
                          <span className="board-card-id-group">
                            <button
                              type="button"
                              className={`issue-cover-btn ${isCovered ? "covered" : ""}`}
                              aria-pressed={isCovered}
                              aria-label={
                                isCovered
                                  ? `Unmark #${card.iid} as covered today`
                                  : `Mark #${card.iid} as covered today`
                              }
                              title={
                                isCovered
                                  ? "Covered today — click to unmark"
                                  : "Mark as covered today"
                              }
                              onClick={(e) => {
                                e.stopPropagation();
                                onToggleCovered(card.id);
                              }}
                            >
                              {isCovered && <Check size={11} strokeWidth={3} aria-hidden="true" />}
                            </button>
                            <span className="board-card-iid">#{card.iid}</span>
                            {getChildTaskCount(card) > 0 && (
                              <span
                                className="issue-children-badge"
                                title={`${getChildTaskCount(card)} child task${getChildTaskCount(card) === 1 ? "" : "s"}`}
                                aria-label={`${getChildTaskCount(card)} child task${getChildTaskCount(card) === 1 ? "" : "s"}`}
                              >
                                <ListTree size={11} aria-hidden="true" />
                                <span>{getChildTaskCount(card)}</span>
                              </span>
                            )}
                            {isActive && (
                              <span className="issue-viewing-tag" title="Currently viewing">
                                Viewing
                              </span>
                            )}
                          </span>
                          <span
                            className="prio-badge"
                            style={{
                              padding: "0 7px",
                              fontSize: "0.7rem",
                              backgroundColor: hexWithAlpha(prioColor, 0.16),
                              color: prioColor,
                            }}
                          >
                            {prio}
                          </span>
                        </div>
                        {card.web_url ? (
                          <a
                            href={card.web_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="board-card-title"
                            onClick={() => onOpenIssue(card.id)}
                            onAuxClick={(e) => {
                              if (e.button === 1) onOpenIssue(card.id);
                            }}
                          >
                            {card.title}
                          </a>
                        ) : (
                          <span
                            className="board-card-title"
                            style={{ cursor: "pointer" }}
                            onClick={() => onOpenIssue(card.id)}
                          >
                            {card.title}
                          </span>
                        )}
                        <div className="board-card-foot">
                          <span
                            style={{
                              overflow: "hidden",
                              textOverflow: "ellipsis",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {card.assignee}
                          </span>
                          <span
                            className={`board-card-days ${card.is_stale ? "stale" : ""}`}
                            title={
                              card.is_stale ? "Stale: no recent update" : "Days in current stage"
                            }
                          >
                            {card.days_in_stage}d
                          </span>
                        </div>
                      </article>
                    );
                  })
                )}
                {remaining > 0 && (
                  <div
                    style={{
                      gridColumn: "1 / -1",
                      fontSize: "0.75rem",
                      color: "var(--muted)",
                      padding: "0.2rem 0.25rem",
                    }}
                  >
                    +{remaining} more on next pages
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
