import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AdminModal } from "./components/AdminModal";
import { IssuePanel } from "./components/IssuePanel";
import { OverviewWorkspace } from "./components/OverviewWorkspace";
import { ScopeBar } from "./components/ScopeBar";
import { SettingsWorkspace } from "./components/settings/SettingsWorkspace";
import { SummaryBar } from "./components/SummaryBar";
import { TopBar } from "./components/TopBar";
import {
  adminLogin,
  adminLogout,
  fetchAdminStatus,
  fetchDashboard,
  IS_DEMO,
} from "./lib/api";
import { getOverviewStages, getWorkflowStages } from "./lib/board";
import {
  applyGlobalFilters,
  applyPreMilestoneFilters,
  buildUrlSearch,
  deriveScopedFilterOptions,
  parseGlobalFiltersUrl,
  parseUrlState,
  resolvePresetDates,
} from "./lib/facets";
import { buildSummaryGroups, type SummaryItem } from "./lib/summary";
import type {
  ActiveChartId,
  DashboardPayload,
  GlobalFilters,
  IssueFacets,
  IssueViewMode,
  ThemeMode,
  ValueMode,
} from "./lib/types";

function getInitialTheme(): ThemeMode {
  try {
    const saved = localStorage.getItem("pulse_theme");
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    // ignore storage restriction
  }
  return "dark";
}

function getInitialValueMode(): ValueMode {
  try {
    const saved = localStorage.getItem("pulse_value_mode");
    if (saved === "count" || saved === "percent") return saved;
  } catch {
    // ignore storage restriction
  }
  return "count";
}

export function App() {
  const initialUrl = useMemo(() => parseUrlState(window.location.search), []);
  const initialGlobal = useMemo(() => parseGlobalFiltersUrl(window.location.search), []);

  const [payload, setPayload] = useState<DashboardPayload | null>(null);
  const payloadRef = useRef<DashboardPayload | null>(null);
  payloadRef.current = payload;

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [theme, setTheme] = useState<ThemeMode>(getInitialTheme);
  const [valueMode, setValueMode] = useState<ValueMode>(getInitialValueMode);
  const [chartsVisible, setChartsVisible] = useState(initialUrl.chartsVisible);
  const [viewMode, setViewMode] = useState<IssueViewMode>("table");
  const [summaryId, setSummaryId] = useState<string | null>(initialUrl.summaryId);
  const [facets, setFacets] = useState<IssueFacets>(initialUrl.facets);
  const [activeChart, setActiveChart] = useState<ActiveChartId>(null);

  const [adminModalOpen, setAdminModalOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  const [globalFilters, setGlobalFilters] = useState<GlobalFilters>(() => ({
    team: initialGlobal.team ?? "All",
    context: initialGlobal.context ?? "All",
    milestone: initialGlobal.milestone ?? "All",
    startDate: initialGlobal.startDate ?? "",
    endDate: initialGlobal.endDate ?? "",
    preset: initialGlobal.preset ?? "all",
  }));

  const loadData = useCallback(async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setLoadError(null);
    try {
      const data = await fetchDashboard();
      setPayload(data);
      const minD = data.filter_options.min_date ?? "";
      const maxD = data.filter_options.max_date ?? "";
      setGlobalFilters((prev) => {
        const team =
          prev.team !== "All" && data.filter_options.teams.includes(prev.team)
            ? prev.team
            : "All";
        const validContexts = deriveScopedFilterOptions(
          data.issues,
          { team, context: "All" },
          data.filter_options,
        ).contexts;
        const context =
          prev.context !== "All" && validContexts.includes(prev.context)
            ? prev.context
            : "All";
        const validMilestones = deriveScopedFilterOptions(
          data.issues,
          { team, context },
          data.filter_options,
        ).milestones;
        const milestone =
          prev.milestone !== "All" && validMilestones.includes(prev.milestone)
            ? prev.milestone
            : "All";
        const dates = resolvePresetDates(prev.preset, minD, maxD, prev.startDate, prev.endDate);
        return {
          team,
          context,
          milestone,
          preset: prev.preset,
          startDate: dates.startDate,
          endDate: dates.endDate,
        };
      });
    } catch (err) {
      setLoadError(err instanceof Error ? err.message : "Failed to load dashboard data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadData(false);
    if (IS_DEMO) return;
    void fetchAdminStatus()
      .then((res) => setIsAdmin(res.authenticated))
      .catch(() => setIsAdmin(false));
  }, [loadData]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("pulse_theme", theme);
    } catch {
      // ignore
    }
  }, [theme]);

  useEffect(() => {
    try {
      localStorage.setItem("pulse_value_mode", valueMode);
    } catch {
      // ignore
    }
  }, [valueMode]);

  useEffect(() => {
    if (!payload) return;
    const nextSearch = buildUrlSearch(chartsVisible, summaryId, facets, globalFilters);
    if (window.location.search !== nextSearch) {
      const nextUrl = `${window.location.pathname}${nextSearch}${window.location.hash}`;
      window.history.replaceState(null, "", nextUrl);
    }
  }, [payload, chartsVisible, summaryId, facets, globalFilters]);

  useEffect(() => {
    const onPopState = () => {
      const parsed = parseUrlState(window.location.search);
      const parsedGlobal = parseGlobalFiltersUrl(window.location.search);
      const curPayload = payloadRef.current;
      const minD = curPayload?.filter_options.min_date ?? "";
      const maxD = curPayload?.filter_options.max_date ?? "";
      const preset = parsedGlobal.preset ?? "all";
      const dates = resolvePresetDates(
        preset,
        minD,
        maxD,
        parsedGlobal.startDate ?? "",
        parsedGlobal.endDate ?? "",
      );
      setChartsVisible(parsed.chartsVisible);
      setSummaryId(parsed.summaryId);
      setFacets(parsed.facets);
      setGlobalFilters({
        team: parsedGlobal.team ?? "All",
        context: parsedGlobal.context ?? "All",
        milestone: parsedGlobal.milestone ?? "All",
        preset,
        startDate: dates.startDate,
        endDate: dates.endDate,
      });
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, []);

  const defaultStartDate = payload?.filter_options.min_date ?? "";
  const defaultEndDate = payload?.filter_options.max_date ?? "";

  const activePalette = useMemo(() => {
    if (!payload) return {};
    return theme === "dark" ? payload.palettes.dark : payload.palettes.light;
  }, [payload, theme]);

  const priorityOrder = payload?.palettes.priority_order ?? [];

  const scopedFilterOptions = useMemo(
    () =>
      payload
        ? deriveScopedFilterOptions(payload.issues, globalFilters, payload.filter_options)
        : { teams: [], contexts: [], milestones: [] },
    [payload, globalFilters],
  );

  const preMilestoneIssues = useMemo(
    () => (payload ? applyPreMilestoneFilters(payload.issues, globalFilters) : []),
    [payload, globalFilters],
  );

  const scopedIssues = useMemo(
    () => (payload ? applyGlobalFilters(payload.issues, globalFilters) : []),
    [payload, globalFilters],
  );

  const overviewStages = useMemo(() => getOverviewStages(scopedIssues), [scopedIssues]);
  const workflowStages = useMemo(() => getWorkflowStages(scopedIssues), [scopedIssues]);

  const summaryGroups = useMemo(
    () => buildSummaryGroups(scopedIssues, activePalette, priorityOrder, theme),
    [scopedIssues, activePalette, priorityOrder, theme],
  );

  const handleChangeGlobalFilters = (next: GlobalFilters) => {
    if (!payload) {
      setGlobalFilters(next);
      return;
    }
    const validForTeam = deriveScopedFilterOptions(
      payload.issues,
      { team: next.team, context: "All" },
      payload.filter_options,
    );
    const context =
      next.context !== "All" && validForTeam.contexts.includes(next.context)
        ? next.context
        : "All";
    const validForContext = deriveScopedFilterOptions(
      payload.issues,
      { team: next.team, context },
      payload.filter_options,
    );
    const milestone =
      next.milestone !== "All" && validForContext.milestones.includes(next.milestone)
        ? next.milestone
        : "All";
    setGlobalFilters({ ...next, context, milestone });
  };

  const handleApplyIssueQueryFromScope = (query: string) => {
    setSummaryId(null);
    setActiveChart(null);
    setFacets((prev) => ({ ...prev, query }));
  };

  const handleToggleMilestone = (title: string) => {
    setGlobalFilters((prev) => ({
      ...prev,
      milestone: prev.milestone === title ? "All" : title,
    }));
  };

  const handleSelectSummary = (item: SummaryItem, isCurrentlyActive: boolean) => {
    setActiveChart(null);
    if (isCurrentlyActive) {
      setSummaryId(null);
      setFacets((prev) => (prev.query ? { query: prev.query } : {}));
    } else {
      setSummaryId(item.itemId);
      setFacets((prev) => (prev.query ? { ...item.facets, query: prev.query } : { ...item.facets }));
    }
  };

  const handleFacetsChange = (next: IssueFacets) => {
    setSummaryId(null);
    setActiveChart(null);
    setFacets(next);
  };

  const handleRemoveSidebarFilter = (key: string) => {
    setGlobalFilters((prev) => {
      if (key === "team") return { ...prev, team: "All" };
      if (key === "context") return { ...prev, context: "All" };
      if (key === "milestone") return { ...prev, milestone: "All" };
      if (key === "date_range") {
        return {
          ...prev,
          startDate: defaultStartDate,
          endDate: defaultEndDate,
          preset: "all",
        };
      }
      return prev;
    });
  };

  const handleClearAll = () => {
    setSummaryId(null);
    setActiveChart(null);
    setFacets({});
    setGlobalFilters({
      team: "All",
      context: "All",
      milestone: "All",
      startDate: defaultStartDate,
      endDate: defaultEndDate,
      preset: "all",
    });
  };

  const handleAdminLogin = async (password: string) => {
    const res = await adminLogin(password);
    setIsAdmin(res.authenticated);
  };

  const handleAdminLogout = async () => {
    const res = await adminLogout();
    setIsAdmin(res.authenticated);
  };

  const activeMilestone = globalFilters.milestone !== "All" ? globalFilters.milestone : null;
  const hasCockpit =
    !loading &&
    !loadError &&
    Boolean(payload && payload.issues.length > 0 && scopedIssues.length > 0);

  return (
    <div className="pulse-app">
      <TopBar
        chartsVisible={chartsVisible}
        theme={theme}
        valueMode={valueMode}
        isAdmin={isAdmin}
        syncStatus={payload?.sync_status}
        version={payload?.version}
        refreshing={refreshing}
        onRefreshData={() => void loadData(true)}
        onToggleCharts={() => setChartsVisible((v) => !v)}
        onChangeValueMode={setValueMode}
        onToggleTheme={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
        onOpenAdmin={() => setAdminModalOpen(true)}
        onOpenSettings={() => setSettingsOpen(true)}
        scopeBar={
          payload && (
            <ScopeBar
              issues={payload.issues}
              filters={globalFilters}
              options={scopedFilterOptions}
              minDate={defaultStartDate}
              maxDate={defaultEndDate}
              matchedCount={scopedIssues.length}
              totalCount={payload.issues.length}
              onChangeFilters={handleChangeGlobalFilters}
              onApplyIssueQuery={handleApplyIssueQueryFromScope}
            />
          )
        }
      />

      {!IS_DEMO && (
        <AdminModal
          open={adminModalOpen}
          isAdmin={isAdmin}
          onClose={() => setAdminModalOpen(false)}
          onLogin={handleAdminLogin}
          onLogout={handleAdminLogout}
          onReloadDashboard={() => loadData(true)}
        />
      )}

      {!IS_DEMO && (
        <SettingsWorkspace
          open={settingsOpen}
          isAdmin={isAdmin}
          issues={payload?.issues ?? []}
          labelStyles={payload?.label_styles ?? {}}
          onClose={() => setSettingsOpen(false)}
          onLogin={handleAdminLogin}
          onReloadDashboard={() => loadData(true)}
        />
      )}

      <main className={hasCockpit ? "pulse-main analytics-cockpit" : "pulse-main"}>
        {loading ? (
          <div className="pulse-panel" style={{ padding: "2rem", textAlign: "center" }}>
            Loading analytics dataset...
          </div>
        ) : loadError ? (
          <div
            className="pulse-panel"
            style={{
              padding: "1.5rem",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "1rem",
              borderColor: "var(--node-pink)",
            }}
          >
            <span>{loadError}</span>
            <button type="button" className="pulse-btn-primary" onClick={() => void loadData(false)}>
              Retry
            </button>
          </div>
        ) : !payload || payload.issues.length === 0 ? (
          <div className="pulse-panel" style={{ padding: "2rem", textAlign: "center", color: "var(--muted)" }}>
            No analytics data available yet. Run the collector & processor or seed local data via Admin Ops.
          </div>
        ) : scopedIssues.length === 0 ? (
          <div className="pulse-panel" style={{ padding: "1.5rem", textAlign: "center" }}>
            <p style={{ margin: "0 0 0.75rem", color: "var(--muted)" }}>
              No issues match the current filters.
            </p>
            <button type="button" className="pulse-btn-secondary" onClick={handleClearAll}>
              Reset filters
            </button>
          </div>
        ) : (
          <OverviewWorkspace
            chartsVisible={chartsVisible}
            viewMode={viewMode}
            issues={scopedIssues}
            timelineIssues={preMilestoneIssues}
            workflowStages={workflowStages}
            activeMilestone={activeMilestone}
            facets={facets}
            activeChart={activeChart}
            palette={activePalette}
            priorityOrder={priorityOrder}
            theme={theme}
            valueMode={valueMode}
            onSelectMilestone={handleToggleMilestone}
            onSetChartFilter={(chartId, nextFacets) => {
              setSummaryId(null);
              setActiveChart(chartId);
              setFacets(nextFacets);
            }}
            issuePanel={
              <IssuePanel
                issues={scopedIssues}
                overviewStages={overviewStages}
                facets={facets}
                globalFilters={globalFilters}
                defaultStartDate={defaultStartDate}
                defaultEndDate={defaultEndDate}
                chartsVisible={chartsVisible}
                viewMode={viewMode}
                labelStyles={payload.label_styles}
                palette={activePalette}
                priorityOrder={priorityOrder}
                theme={theme}
                valueMode={valueMode}
                summaryBar={
                  <SummaryBar
                    groups={summaryGroups}
                    activeSummaryId={summaryId}
                    facets={facets}
                    onSelectSummary={handleSelectSummary}
                  />
                }
                onChangeViewMode={setViewMode}
                onChangeFacets={handleFacetsChange}
                onRemoveSidebarFilter={handleRemoveSidebarFilter}
                onClearAll={handleClearAll}
              />
            }
          />
        )}
      </main>
    </div>
  );
}
