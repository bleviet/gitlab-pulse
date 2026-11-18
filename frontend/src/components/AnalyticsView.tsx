import { useEffect, useRef, useState } from "react";
import { withoutFacet } from "../lib/facets";
import type { ActiveChartId, IssueFacets, IssueItem, ThemeMode } from "../lib/types";
import { DailyVelocityChart } from "./charts/DailyVelocityChart";
import { PriorityDonut } from "./charts/PriorityDonut";
import { QualitySignalsChart } from "./charts/QualitySignalsChart";
import { ReleaseTimeline } from "./charts/ReleaseTimeline";
import { WorkflowStateRow } from "./charts/WorkflowStateRow";

interface AnalyticsViewProps {
  issues: IssueItem[];
  timelineIssues: IssueItem[];
  overviewStages: string[];
  activeMilestone: string | null;
  facets: IssueFacets;
  activeChart: ActiveChartId;
  palette: Record<string, string>;
  priorityOrder: string[];
  theme: ThemeMode;
  onSelectMilestone: (title: string) => void;
  onSetChartFilter: (chartId: ActiveChartId, nextFacets: IssueFacets) => void;
  issuePanel: React.ReactNode;
}

export function AnalyticsView({
  issues,
  timelineIssues,
  overviewStages,
  activeMilestone,
  facets,
  activeChart,
  palette,
  priorityOrder,
  theme,
  onSelectMilestone,
  onSetChartFilter,
  issuePanel,
}: AnalyticsViewProps) {
  const flowRef = useRef<HTMLDivElement | null>(null);
  const workflowRef = useRef<HTMLDivElement | null>(null);
  const [pinned, setPinned] = useState(true);

  useEffect(() => {
    const measure = () => {
      const wfEl = workflowRef.current;
      const flowEl = flowRef.current;
      if (!wfEl || !flowEl) return;
      const wfHeight = wfEl.offsetHeight;
      const fits = wfHeight + 250 <= window.innerHeight - 52;
      setPinned(fits);
      flowEl.style.setProperty("--workflow-sticky-h", fits ? `${wfHeight}px` : "0px");
    };

    measure();
    window.addEventListener("resize", measure);
    let ro: ResizeObserver | null = null;
    if (workflowRef.current && typeof ResizeObserver !== "undefined") {
      ro = new ResizeObserver(measure);
      ro.observe(workflowRef.current);
    }
    return () => {
      window.removeEventListener("resize", measure);
      ro?.disconnect();
    };
  }, [overviewStages.length]);

  const keepQuery = (): IssueFacets => (facets.query ? { query: facets.query } : {});

  const handleDonutSlice = (stateFilter: "opened" | "closed", priority: string) => {
    const chartId: ActiveChartId = stateFilter === "opened" ? "open_donut" : "closed_donut";
    const isSame =
      activeChart === chartId &&
      facets.state === stateFilter &&
      facets.priority?.toLowerCase() === priority.toLowerCase();
    if (isSame) {
      onSetChartFilter(null, keepQuery());
    } else {
      onSetChartFilter(chartId, { ...keepQuery(), state: stateFilter, priority });
    }
  };

  const handleDonutCenter = (stateFilter: "opened" | "closed") => {
    const chartId: ActiveChartId = stateFilter === "opened" ? "open_donut" : "closed_donut";
    const isSame = activeChart === chartId && facets.state === stateFilter && !facets.priority;
    if (isSame) {
      onSetChartFilter(null, keepQuery());
    } else {
      onSetChartFilter(chartId, { ...keepQuery(), state: stateFilter });
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
        state: kind === "closed" ? "closed" : "opened",
      });
    }
  };

  const handleStageBar = (stage: string, priority: string) => {
    const idx = Math.max(0, overviewStages.indexOf(stage));
    const chartId: ActiveChartId = `stage_bar_${idx}`;
    const isSame =
      activeChart?.startsWith("stage_bar_") &&
      facets.stage === stage &&
      facets.priority?.toLowerCase() === priority.toLowerCase();
    if (isSame) {
      onSetChartFilter(null, withoutFacet(withoutFacet(keepQuery(), "stage"), "priority"));
    } else {
      onSetChartFilter(chartId, {
        ...keepQuery(),
        stage,
        state: "opened",
        priority,
      });
    }
  };

  const isStageBarActive = Boolean(activeChart && activeChart.startsWith("stage_bar_"));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
      <div className="analytics-grid">
        <div className="pulse-panel col-span-9">
          <div className="pulse-panel-head">
            <span className="pulse-panel-title">Release Timeline</span>
            <span className="pulse-panel-meta">Milestones</span>
          </div>
          <ReleaseTimeline
            issues={timelineIssues}
            palette={palette}
            highlightMilestone={activeMilestone}
            variant="analytics"
            onSelectMilestone={onSelectMilestone}
          />
        </div>

        <div className="pulse-panel col-span-3">
          <div className="pulse-panel-head">
            <span className="pulse-panel-title">Closed Issues by Priority</span>
          </div>
          <PriorityDonut
            issues={issues}
            stateFilter="closed"
            centerCaption={"CLOSED\nISSUES"}
            palette={palette}
            priorityOrder={priorityOrder}
            theme={theme}
            activePriority={activeChart === "closed_donut" ? (facets.priority ?? null) : null}
            isCenterSelected={
              activeChart === "closed_donut" && facets.state === "closed" && !facets.priority
            }
            onSelectSlice={(prio) => handleDonutSlice("closed", prio)}
            onSelectCenter={() => handleDonutCenter("closed")}
          />
        </div>

        <div className="pulse-panel col-span-3">
          <div className="pulse-panel-head">
            <span className="pulse-panel-title">Open Issues by Priority</span>
          </div>
          <PriorityDonut
            issues={issues}
            stateFilter="opened"
            centerCaption={"OPEN\nISSUES"}
            palette={palette}
            priorityOrder={priorityOrder}
            theme={theme}
            activePriority={activeChart === "open_donut" ? (facets.priority ?? null) : null}
            isCenterSelected={
              activeChart === "open_donut" && facets.state === "opened" && !facets.priority
            }
            onSelectSlice={(prio) => handleDonutSlice("opened", prio)}
            onSelectCenter={() => handleDonutCenter("opened")}
          />
        </div>

        <div className="pulse-panel col-span-3">
          <div className="pulse-panel-head">
            <span className="pulse-panel-title">Issue Quality Signals</span>
            <span className="pulse-panel-meta">Hints</span>
          </div>
          <QualitySignalsChart
            issues={issues}
            palette={palette}
            activeSignal={
              activeChart === "quality_signal_chart" ? (facets.signal ?? null) : null
            }
            onSelectSignal={handleQualitySignal}
          />
        </div>

        <div className="pulse-panel col-span-6">
          <div className="pulse-panel-head">
            <span className="pulse-panel-title">Daily New vs. Closed Issues</span>
          </div>
          <DailyVelocityChart
            issues={issues}
            palette={palette}
            activeDay={activeChart === "velocity_chart" ? (facets.day ?? null) : null}
            activeDayKind={activeChart === "velocity_chart" ? (facets.day_kind ?? null) : null}
            onSelectPoint={handleVelocityPoint}
          />
        </div>
      </div>

      <div ref={flowRef} className="analytics-flow-section">
        <div
          ref={workflowRef}
          className={`analytics-workflow-sticky ${pinned ? "" : "unpinned"}`}
        >
          <div className="pulse-panel-head">
            <span className="pulse-panel-title">Issues by Workflow State</span>
          </div>
          <WorkflowStateRow
            issues={issues}
            stages={overviewStages}
            palette={palette}
            priorityOrder={priorityOrder}
            theme={theme}
            activeStage={isStageBarActive ? (facets.stage ?? null) : null}
            activePriority={isStageBarActive ? (facets.priority ?? null) : null}
            isStageChartFilterActive={isStageBarActive}
            onSelectBar={handleStageBar}
          />
        </div>

        {issuePanel}
      </div>
    </div>
  );
}
