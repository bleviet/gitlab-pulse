import type { ReactNode } from "react";
import { BarChart3, Moon, RefreshCw, Shield, Sun } from "lucide-react";
import { IS_DEMO } from "../lib/api";
import type { SyncStatus, ThemeMode, ValueMode } from "../lib/types";

interface TopBarProps {
  chartsVisible: boolean;
  theme: ThemeMode;
  valueMode: ValueMode;
  isAdmin: boolean;
  scopeBar?: ReactNode;
  syncStatus?: SyncStatus;
  version?: string;
  refreshing: boolean;
  onRefreshData: () => void;
  onToggleCharts: () => void;
  onChangeValueMode: (mode: ValueMode) => void;
  onToggleTheme: () => void;
  onOpenAdmin: () => void;
}

export function TopBar({
  chartsVisible,
  theme,
  valueMode,
  isAdmin,
  scopeBar,
  syncStatus,
  version,
  refreshing,
  onRefreshData,
  onToggleCharts,
  onChangeValueMode,
  onToggleTheme,
  onOpenAdmin,
}: TopBarProps) {
  const isSyncError = Boolean(syncStatus && /error|fail/i.test(syncStatus.status));
  const syncTitle = syncStatus
    ? `Status: ${syncStatus.status} · Last sync: ${syncStatus.last_sync}${version ? ` · v${version}` : ""} — Click to refresh`
    : "Refresh dashboard data";

  return (
    <header className="pulse-topbar">
      <div className="pulse-topbar-left">
        <div className="pulse-brand">
          <img
            src={`${import.meta.env.BASE_URL}static/logo.svg`}
            alt=""
            width={28}
            height={28}
            style={{ borderRadius: "7px", display: "block" }}
          />
          <span className="pulse-brand-title">
            <span className="pulse-brand-accent">GitLab</span>Pulse
          </span>
        </div>
      </div>

      {scopeBar && <div className="pulse-topbar-center">{scopeBar}</div>}

      <div className="pulse-topbar-right">
        {IS_DEMO && (
          <a
            className="pulse-icon-btn"
            href="https://github.com/bleviet/gitlab-pulse#quick-start-synthetic-demo"
            target="_blank"
            rel="noopener noreferrer"
            title="Run GitLab Pulse locally with synthetic data"
          >
            Demo · synthetic data
          </a>
        )}

        {!IS_DEMO && syncStatus && (
          <button
            type="button"
            className="pulse-icon-btn"
            disabled={refreshing}
            onClick={onRefreshData}
            title={syncTitle}
            aria-label={`Refresh data (${syncStatus.status}, last sync ${syncStatus.last_sync})`}
          >
            <span
              className={`scope-status-dot${isSyncError ? " error" : ""}`}
              aria-hidden="true"
            />
            <RefreshCw size={14} className={refreshing ? "pulse-spin" : undefined} />
          </button>
        )}

        <button
          type="button"
          className="pulse-icon-btn pulse-toggle-btn"
          aria-pressed={chartsVisible}
          onClick={onToggleCharts}
          title={chartsVisible ? "Hide analytics charts" : "Show analytics charts"}
        >
          <BarChart3 size={14} />
          <span>Charts</span>
        </button>

        <div className="pulse-segmented" role="group" aria-label="Show numbers as">
          <button
            type="button"
            aria-pressed={valueMode === "count"}
            title="Show counts"
            onClick={() => onChangeValueMode("count")}
          >
            #
          </button>
          <button
            type="button"
            aria-pressed={valueMode === "percent"}
            title="Show percentages"
            onClick={() => onChangeValueMode("percent")}
          >
            %
          </button>
        </div>

        <button
          type="button"
          className="pulse-icon-btn"
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
          onClick={onToggleTheme}
          title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
        >
          {theme === "dark" ? <Sun size={15} /> : <Moon size={15} />}
        </button>

        {!IS_DEMO && (
          <button
            type="button"
            className="pulse-icon-btn"
            aria-label="Open admin operations"
            onClick={onOpenAdmin}
            title="Admin operations"
          >
            <Shield size={15} color={isAdmin ? "var(--accent)" : undefined} />
            <span>{isAdmin ? "Admin" : "Ops"}</span>
          </button>
        )}
      </div>
    </header>
  );
}
