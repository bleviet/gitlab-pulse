import { useEffect, useMemo, useState, type ReactNode } from "react";
import { buildIssueTypeDonutData, buildPriorityDonutData } from "../lib/analytics";
import type {
  ActiveChartId,
  IssueFacets,
  IssueItem,
  IssueViewMode,
  ThemeMode,
} from "../lib/types";
import { DailyVelocityChart } from "./charts/DailyVelocityChart";
import { PriorityDonut } from "./charts/PriorityDonut";
import { QualitySignalsChart } from "./charts/QualitySignalsChart";
import { ReleaseTimeline } from "./charts/ReleaseTimeline";
import { WorkflowStateRow } from "./charts/WorkflowStateRow";

interface OverviewWorkspaceProps {
  chartsVisible: boolean;
  viewMode: IssueViewMode;
  issues: IssueItem[];
  timelineIssues: IssueItem[];
  workflowStages: string[];
  activeMilestone: string | null;
  facets: IssueFacets;
  activeChart: ActiveChartId;
  palette: Record<string, string>;
  priorityOrder: string[];
  theme: ThemeMode;
  onSelectMilestone: (title: string) => void;
  onSetChartFilter: (chartId: ActiveChartId, nextFacets: IssueFacets) => void;
  issuePanel: ReactNode;
}

export function OverviewWorkspace({
  chartsVisible,
  viewMode,
  issues,
  timelineIssues,
  workflowStages,
  activeMilestone,
  facets,
  activeChart,
  palette,
  priorityOrder,
  theme,
  onSelectMilestone,
  onSetChartFilter,
  issuePanel,
}: OverviewWorkspaceProps) {
  const [isWideScreen, setIsWideScreen] = useState(() =>
    typeof window !== "undefined" && typeof window.matchMedia === "function"
      ? window.matchMedia("(min-width: 1360px)").matches
      : true,
  );

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") return;
    const mq = window.matchMedia("(min-width: 1360px)");
    const onChange = (e: MediaQueryListEvent) => setIsWideScreen(e.matches);
    setIsWideScreen(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  const keepQuery = (): IssueFacets => (facets.query ? { query: facets.query } : {});

  const openPriorityModel = useMemo(
    () => buildPriorityDonutData(issues, "opened", palette, priorityOrder, theme),
    [issues, palette, priorityOrder, theme],
  );

  const openTypeModel = useMemo(
    () => buildIssueTypeDonutData(issues, "opened", palette, theme),
    [issues, palette, theme],
  );

  const handlePrioritySlice = (priority: string) => {
    const isSame =
      activeChart === "open_donut" &&
      facets.state === "opened" &&
      facets.priority?.toLowerCase() === priority.toLowerCase();
    if (isSame) {
      onSetChartFilter(null, keepQuery());
    } else {
      onSetChartFilter("open_donut", { ...keepQuery(), state: "opened", priority });
    }
  };

  const handleTypeSlice = (issueType: string) => {
    const isSame =
      activeChart === "type_donut" &&
      facets.state === "opened" &&
      facets.issue_type?.toLowerCase() === issueType.toLowerCase();
    if (isSame) {
      onSetChartFilter(null, keepQuery());
    } else {
      onSetChartFilter("type_donut", { ...keepQuery(), state: "opened", issue_type: issueType });
    }
  };

  const handleOpenCenter = (chartId: "open_donut" | "type_donut") => {
    const isSame =
      activeChart === chartId &&
      facets.state === "opened" &&
      !facets.priority &&
      !facets.issue_type;
    if (isSame) {
      onSetChartFilter(null, keepQuery());
    } else {
      onSetChartFilter(chartId, { ...keepQuery(), state: "opened" });
    }
  };

  const handleQualitySignal = (signalCode: string) => {
    const isSame = activeChart === "quality_signal_chart" && facets.signal === signalCode;
    if (isSame) {
      onSetChartFilter(null, keepQuery());
    } else {
      onSetChartFilter("quality_signal_chart", { ...keepQuery(), signal: signalCode });
    }
  };

  const handleVelocityPoint = (isoDate: string, kind: "created" | "closed") => {
    const isSame =
      activeChart === "velocity_chart" && facets.day === isoDate && facets.day_kind === kind;
    if (isSame) {
      onSetChartFilter(null, keepQuery());
    } else {
      onSetChartFilter("velocity_chart", {
        ...keepQuery(),
        day: isoDate,
        day_kind: kind,
        state: kind === "closed" ? "closed" : "all",
      });
    }
  };

  const handleStageBar = (
    stage: string,
    priority: string,
    filterState: "opened" | "closed" | "all",
  ) => {
    const idx = Math.max(0, workflowStages.indexOf(stage));
    const chartId: ActiveChartId = `stage_bar_${idx}`;
    const isSame =
      activeChart?.startsWith("stage_bar_") &&
      facets.stage === stage &&
      facets.state === filterState &&
      facets.priority?.toLowerCase() === priority.toLowerCase();
    if (isSame) {
      onSetChartFilter(null, keepQuery());
    } else {
      onSetChartFilter(chartId, {
        ...keepQuery(),
        stage,
        state: filterState,
        priority,
      });
    }
  };

  const handleStageOnly = (stage: string, filterState: "opened" | "closed" | "all") => {
    const idx = Math.max(0, workflowStages.indexOf(stage));
    const chartId: ActiveChartId = `stage_bar_${idx}`;
    const isSame =
      activeChart?.startsWith("stage_bar_") &&
      facets.stage === stage &&
      facets.state === filterState &&
      !facets.priority;
    if (isSame) {
      onSetChartFilter(null, keepQuery());
    } else {
      onSetChartFilter(chartId, {
        ...keepQuery(),
        stage,
        state: filterState,
      });
    }
  };

  const isStageBarActive = Boolean(activeChart && activeChart.startsWith("stage_bar_"));
  const isWideSplit = isWideScreen && viewMode === "table" && chartsVisible;
  const donutSize = isWideSplit ? 120 : 110;
  const createdLegendColor = palette.opened ?? "#4facfe";
  const closedLegendColor = palette.closed ?? "#56d4b0";

  const renderChartCards = () => (
    <>
      <div className="pulse-panel">
        <div className="pulse-panel-head">
          <span className="pulse-panel-title">Open Mix</span>
          <span className="pulse-panel-meta">Priority · Type</span>
        </div>
        <div className="priority-mix-pair">
          <PriorityDonut
            model={openPriorityModel}
            centerCaption={"OPEN\nPRIORITY"}
            ariaLabel="Open issues by priority donut chart"
            emptyMessage="No open issues."
            centerTooltipSubject="open"
            size={donutSize}
            activeSlice={activeChart === "open_donut" ? (facets.priority ?? null) : null}
            isCenterSelected={
              activeChart === "open_donut" && facets.state === "opened" && !facets.priority
            }
            onSelectSlice={handlePrioritySlice}
            onSelectCenter={() => handleOpenCenter("open_donut")}
          />
          <PriorityDonut
            model={openTypeModel}
            centerCaption={"OPEN\nBY TYPE"}
            ariaLabel="Open issues by type donut chart"
            emptyMessage="No open issues."
            centerTooltipSubject="open"
            size={donutSize}
            activeSlice={activeChart === "type_donut" ? (facets.issue_type ?? null) : null}
            isCenterSelected={
              activeChart === "type_donut" && facets.state === "opened" && !facets.issue_type
            }
            onSelectSlice={handleTypeSlice}
            onSelectCenter={() => handleOpenCenter("type_donut")}
          />
        </div>
      </div>

      <div className="pulse-panel">
        <div className="pulse-panel-head">
          <span className="pulse-panel-title">Workflow State</span>
          <span className="pulse-panel-meta">Open · Closed</span>
        </div>
        <WorkflowStateRow
          issues={issues}
          stages={workflowStages}
          palette={palette}
          priorityOrder={priorityOrder}
          theme={theme}
          activeStage={isStageBarActive ? (facets.stage ?? null) : null}
          activePriority={isStageBarActive ? (facets.priority ?? null) : null}
          isStageChartFilterActive={isStageBarActive}
          onSelectBar={handleStageBar}
          onSelectStage={handleStageOnly}
        />
      </div>

      <div className="pulse-panel">
        <div className="pulse-panel-head">
          <span className="pulse-panel-title">Daily New vs. Closed</span>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.65rem",
              fontSize: "0.72rem",
              color: "var(--muted)",
            }}
          >
            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.28rem" }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: 999,
                  background: createdLegendColor,
                }}
              />
              New
            </span>
            <span style={{ display: "inline-flex", alignItems: "center", gap: "0.28rem" }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: 999,
                  background: closedLegendColor,
                }}
              />
              Closed
            </span>
          </div>
        </div>
        <DailyVelocityChart
          issues={issues}
          palette={palette}
          height={isWideSplit ? 112 : 104}
          activeDay={activeChart === "velocity_chart" ? (facets.day ?? null) : null}
          activeDayKind={activeChart === "velocity_chart" ? (facets.day_kind ?? null) : null}
          onSelectPoint={handleVelocityPoint}
        />
      </div>

      <div className="pulse-panel">
        <div className="pulse-panel-head">
          <span className="pulse-panel-title">Issue Quality Signals</span>
          <span className="pulse-panel-meta">Open Hints</span>
        </div>
        <QualitySignalsChart
          issues={issues}
          palette={palette}
          activeSignal={activeChart === "quality_signal_chart" ? (facets.signal ?? null) : null}
          onSelectSignal={handleQualitySignal}
        />
      </div>
    </>
  );

  return (
    <div className="analytics-cockpit-inner">
      <div className="pulse-panel release-rail-panel">
        <ReleaseTimeline
          issues={timelineIssues}
          palette={palette}
          highlightMilestone={activeMilestone}
          variant="compact"
          height={78}
          onSelectMilestone={onSelectMilestone}
        />
      </div>

      <div className={`analytics-workspace ${isWideSplit ? "wide-split" : "top-strip"}`}>
        {isWideSplit ? (
          <aside className="analytics-rail" aria-label="Analytics charts">
            {renderChartCards()}
          </aside>
        ) : (
          chartsVisible && (
            <div className="analytics-bento-strip" aria-label="Analytics charts">
              {renderChartCards()}
            </div>
          )
        )}

        {issuePanel}
      </div>
    </div>
  );
}
