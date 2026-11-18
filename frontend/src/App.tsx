import { useCallback, useEffect, useMemo, useState } from "react";
import { AdminModal } from "./components/AdminModal";
import { AnalyticsView } from "./components/AnalyticsView";
import { ReleaseTimeline } from "./components/charts/ReleaseTimeline";
import { IssuePanel } from "./components/IssuePanel";
import { SidebarDrawer } from "./components/SidebarDrawer";
import { SummaryBar } from "./components/SummaryBar";
import { TopBar } from "./components/TopBar";
import {
  adminLogin,
  adminLogout,
  fetchAdminStatus,
  fetchDashboard,
} from "./lib/api";
import { getOverviewStages } from "./lib/board";
import {
  applyGlobalFilters,
  applyPreMilestoneFilters,
  buildUrlSearch,
  parseUrlState,
} from "./lib/facets";
import { buildSummaryGroups, type SummaryItem } from "./lib/summary";
import type {
  ActiveChartId,
  DashboardPayload,
  GlobalFilters,
  IssueFacets,
  OverviewLayout,
  ThemeMode,
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

export function App() {
  const initialUrl = useMemo(() => parseUrlState(window.location.search), []);

  const [payload, setPayload] = useState<DashboardPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [theme, setTheme] = useState<ThemeMode>(getInitialTheme);
  const [layout, setLayout] = useState<OverviewLayout>(initialUrl.layout);
  const [summaryId, setSummaryId] = useState<string | null>(initialUrl.summaryId);
  const [facets, setFacets] = useState<IssueFacets>(initialUrl.facets);
  const [activeChart, setActiveChart] = useState<ActiveChartId>(null);

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [adminModalOpen, setAdminModalOpen] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  const [globalFilters, setGlobalFilters] = useState<GlobalFilters>({
    team: "All",
    context: "All",
    milestone: "All",
    startDate: "",
    endDate: "",
    preset: "all",
  });

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
        if (prev.preset === "all" && !prev.startDate && !prev.endDate) {
          return { ...prev, startDate: minD, endDate: maxD };
        }
        return prev;
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
    void fetchAdminStatus()
      .then((res) => setIsAdmin(res.authenticated))
      .catch(() => setIsAdmin(false));
  }, [loadData]);

  // Apply theme attribute & persist choice
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("pulse_theme", theme);
    } catch {
      // ignore
    }
  }, [theme]);

  // Sync URL query parameters without reloads
  useEffect(() => {
    const nextSearch = buildUrlSearch(layout, summaryId, facets);
    if (window.location.search !== nextSearch) {
      const nextUrl = `${window.location.pathname}${nextSearch}${window.location.hash}`;
      window.history.replaceState(null, "", nextUrl);
    }
  }, [layout, summaryId, facets]);

  // Handle browser Back / Forward
  useEffect(() => {
    const onPopState = () => {
      const parsed = parseUrlState(window.location.search);
      setLayout(parsed.layout);
      setSummaryId(parsed.summaryId);
      setFacets(parsed.facets);
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

  const preMilestoneIssues = useMemo(
    () => (payload ? applyPreMilestoneFilters(payload.issues, globalFilters) : []),
    [payload, globalFilters],
  );

  const scopedIssues = useMemo(
    () => (payload ? applyGlobalFilters(payload.issues, globalFilters) : []),
    [payload, globalFilters],
  );

  const overviewStages = useMemo(() => getOverviewStages(scopedIssues), [scopedIssues]);

  const summaryGroups = useMemo(
    () => buildSummaryGroups(scopedIssues, activePalette, priorityOrder, theme),
    [scopedIssues, activePalette, priorityOrder, theme],
  );

  const activeSidebarCount = useMemo(() => {
    let count = 0;
    if (globalFilters.team !== "All") count += 1;
    if (globalFilters.context !== "All") count += 1;
    if (globalFilters.milestone !== "All") count += 1;
    if (
      (globalFilters.startDate && globalFilters.startDate !== defaultStartDate) ||
      (globalFilters.endDate && globalFilters.endDate !== defaultEndDate)
    ) {
      count += 1;
    }
    return count;
  }, [globalFilters, defaultStartDate, defaultEndDate]);

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

  const renderIssuePanel = (showFilters: boolean, laneHeaders: boolean) => (
    <IssuePanel
      issues={scopedIssues}
      overviewStages={overviewStages}
      facets={facets}
      globalFilters={globalFilters}
      defaultStartDate={defaultStartDate}
      defaultEndDate={defaultEndDate}
      layout={layout}
      activeChart={activeChart}
      showFilters={showFilters}
      laneHeaders={laneHeaders}
      labelStyles={payload?.label_styles ?? {}}
      palette={activePalette}
      priorityOrder={priorityOrder}
      theme={theme}
      toolbarLeft={
        showFilters ? (
          <SummaryBar
            groups={summaryGroups}
            activeSummaryId={summaryId}
            facets={facets}
            onSelectSummary={handleSelectSummary}
          />
        ) : undefined
      }
      onChangeFacets={handleFacetsChange}
      onRemoveSidebarFilter={handleRemoveSidebarFilter}
      onClearAll={handleClearAll}
      onClearChartFilter={() => {
        setActiveChart(null);
        setFacets((prev) => (prev.query ? { query: prev.query } : {}));
      }}
    />
  );

  return (
    <div className="pulse-app">
      <TopBar
        layout={layout}
        theme={theme}
        activeSidebarCount={activeSidebarCount}
        isAdmin={isAdmin}
        onToggleSidebar={() => setSidebarOpen((v) => !v)}
        onChangeLayout={(next) => {
          if (next === "compact") setActiveChart(null);
          setLayout(next);
        }}
        onToggleTheme={() => setTheme((prev) => (prev === "dark" ? "light" : "dark"))}
        onOpenAdmin={() => setAdminModalOpen(true)}
      />

      {payload && (
        <SidebarDrawer
          open={sidebarOpen}
          filters={globalFilters}
          options={payload.filter_options}
          syncStatus={payload.sync_status}
          version={payload.version}
          isAdmin={isAdmin}
          refreshing={refreshing}
          onClose={() => setSidebarOpen(false)}
          onChangeFilters={setGlobalFilters}
          onRefreshData={() => void loadData(true)}
          onAdminLogin={handleAdminLogin}
          onAdminLogout={handleAdminLogout}
          onOpenAdminModal={() => setAdminModalOpen(true)}
        />
      )}

      <AdminModal
        open={adminModalOpen}
        isAdmin={isAdmin}
        onClose={() => setAdminModalOpen(false)}
        onLogin={handleAdminLogin}
        onLogout={handleAdminLogout}
        onReloadDashboard={() => loadData(true)}
      />

      <main className="pulse-main">
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
              No issues match the current sidebar filters.
            </p>
            <button type="button" className="pulse-btn-secondary" onClick={handleClearAll}>
              Reset filters
            </button>
          </div>
        ) : layout === "analytics" ? (
          <AnalyticsView
            issues={scopedIssues}
            timelineIssues={preMilestoneIssues}
            overviewStages={overviewStages}
            activeMilestone={activeMilestone}
            facets={facets}
            activeChart={activeChart}
            palette={activePalette}
            priorityOrder={priorityOrder}
            theme={theme}
            onSelectMilestone={handleToggleMilestone}
            onSetChartFilter={(chartId, nextFacets) => {
              setSummaryId(null);
              setActiveChart(chartId);
              setFacets(nextFacets);
            }}
            issuePanel={renderIssuePanel(false, false)}
          />
        ) : (
          <>
            <div className="pulse-panel" style={{ padding: "0.5rem 0.85rem" }}>
              <ReleaseTimeline
                issues={preMilestoneIssues}
                palette={activePalette}
                highlightMilestone={activeMilestone}
                variant="compact"
                onSelectMilestone={handleToggleMilestone}
              />
            </div>
            {renderIssuePanel(true, true)}
          </>
        )}
      </main>
    </div>
  );
}
