import { useEffect, useRef, type ReactNode } from "react";
import { BarChart3, Lock, LockOpen, RefreshCw, Shield, X } from "lucide-react";
import { IS_DEMO } from "../lib/api";
import type { UiThemeId } from "../lib/uiThemes";
import type { SyncStatus, ThemeMode, ValueMode } from "../lib/types";
import { ThemePicker } from "./ThemePicker";
import { UnlockForm } from "./settings/UnlockForm";

interface TopBarProps {
  chartsVisible: boolean;
  theme: ThemeMode;
  colorTheme: UiThemeId;
  valueMode: ValueMode;
  isAdmin: boolean;
  editMode: boolean;
  unlockPopoverOpen: boolean;
  scopeBar?: ReactNode;
  syncStatus?: SyncStatus;
  version?: string;
  refreshing: boolean;
  onRefreshData: () => void;
  onToggleCharts: () => void;
  onChangeValueMode: (mode: ValueMode) => void;
  onChangeTheme: (mode: ThemeMode) => void;
  onChangeColorTheme: (themeId: UiThemeId) => void;
  onOpenAdmin: () => void;
  onToggleEditMode: () => void;
  onCloseUnlockPopover: () => void;
  onLogin: (password: string) => Promise<void>;
  onUnlocked: () => void;
}

export function TopBar({
  chartsVisible,
  theme,
  colorTheme,
  valueMode,
  isAdmin,
  editMode,
  unlockPopoverOpen,
  scopeBar,
  syncStatus,
  version,
  refreshing,
  onRefreshData,
  onToggleCharts,
  onChangeValueMode,
  onChangeTheme,
  onChangeColorTheme,
  onOpenAdmin,
  onToggleEditMode,
  onCloseUnlockPopover,
  onLogin,
  onUnlocked,
}: TopBarProps) {
  const unlockAnchorRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!unlockPopoverOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      if (unlockAnchorRef.current && !unlockAnchorRef.current.contains(e.target as Node)) {
        onCloseUnlockPopover();
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onCloseUnlockPopover();
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [unlockPopoverOpen, onCloseUnlockPopover]);

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

        <ThemePicker
          mode={theme}
          colorTheme={colorTheme}
          onChangeMode={onChangeTheme}
          onChangeColorTheme={onChangeColorTheme}
        />

        {!IS_DEMO && (
          <div ref={unlockAnchorRef} className="topbar-unlock-anchor">
            <button
              type="button"
              className={`pulse-icon-btn pulse-toggle-btn${editMode ? " edit-unlocked" : ""}`}
              aria-pressed={editMode}
              aria-expanded={unlockPopoverOpen ? true : undefined}
              aria-label={editMode ? "Lock rules" : "Unlock rules to edit"}
              onClick={onToggleEditMode}
              title={
                editMode
                  ? "Rules unlocked — click to lock"
                  : "Unlock to edit rules directly on the dashboard"
              }
            >
              {editMode ? <LockOpen size={14} /> : <Lock size={14} />}
              <span>{editMode ? "Unlocked" : "Edit"}</span>
            </button>

            {unlockPopoverOpen && (
              <div
                className="scope-popover topbar-unlock-popover"
                role="dialog"
                aria-label="Unlock rule editing"
              >
                <div className="scope-popover-head">
                  <span className="pulse-panel-title">Unlock Editing</span>
                  <button
                    type="button"
                    className="pulse-icon-btn rule-popover-close"
                    aria-label="Close"
                    onClick={onCloseUnlockPopover}
                  >
                    <X size={12} />
                  </button>
                </div>
                <p className="settings-hint">
                  Enter the admin password to edit rules directly on the dashboard.
                </p>
                <UnlockForm onLogin={onLogin} onDone={onUnlocked} />
              </div>
            )}
          </div>
        )}

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
