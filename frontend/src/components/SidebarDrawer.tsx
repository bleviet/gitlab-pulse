import { useEffect, useState, type FormEvent } from "react";
import { Calendar, Filter, RefreshCw, Shield, X } from "lucide-react";
import type { FilterOptions, GlobalFilters, SyncStatus, TimePreset } from "../lib/types";

interface SidebarDrawerProps {
  open: boolean;
  filters: GlobalFilters;
  options: FilterOptions;
  syncStatus: SyncStatus;
  version: string;
  isAdmin: boolean;
  refreshing: boolean;
  onClose: () => void;
  onChangeFilters: (next: GlobalFilters) => void;
  onRefreshData: () => void;
  onAdminLogin: (password: string) => Promise<void>;
  onAdminLogout: () => Promise<void>;
  onOpenAdminModal: () => void;
}

function subtractDaysIso(endIso: string, days: number, minIso: string): string {
  const endMs = Date.parse(`${endIso}T00:00:00Z`);
  if (Number.isNaN(endMs)) return minIso;
  const candidate = new Date(endMs - days * 86_400_000).toISOString().slice(0, 10);
  return minIso && candidate < minIso ? minIso : candidate;
}

export function SidebarDrawer({
  open,
  filters,
  options,
  syncStatus,
  version,
  isAdmin,
  refreshing,
  onClose,
  onChangeFilters,
  onRefreshData,
  onAdminLogin,
  onAdminLogout,
  onOpenAdminModal,
}: SidebarDrawerProps) {
  const [password, setPassword] = useState("");
  const [authError, setAuthError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const minDate = options.min_date ?? "";
  const maxDate = options.max_date ?? new Date().toISOString().slice(0, 10);

  const applyPreset = (preset: TimePreset) => {
    if (preset === "all") {
      onChangeFilters({
        ...filters,
        startDate: minDate,
        endDate: maxDate,
        preset: "all",
      });
      return;
    }
    const days = preset === "30d" ? 30 : preset === "90d" ? 90 : 365;
    onChangeFilters({
      ...filters,
      startDate: subtractDaysIso(maxDate, days, minDate),
      endDate: maxDate,
      preset,
    });
  };

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    if (!password) return;
    setSubmitting(true);
    setAuthError(null);
    try {
      await onAdminLogin(password);
      setPassword("");
    } catch (err) {
      setAuthError(err instanceof Error ? err.message : "Invalid password");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <div className="drawer-backdrop" onClick={onClose} aria-hidden="true" />
      <aside className="drawer-panel" aria-label="Dashboard filters and settings">
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div>
            <h2 style={{ fontSize: "1rem" }}>Workspace Filters</h2>
            <span style={{ fontSize: "0.75rem", color: "var(--muted)" }}>Analytics Dashboard</span>
          </div>
          <button
            type="button"
            className="pulse-icon-btn"
            aria-label="Close sidebar"
            onClick={onClose}
          >
            <X size={15} />
          </button>
        </div>

        <section className="drawer-section">
          <div className="drawer-section-title">
            <Filter size={14} />
            <span>Filters</span>
          </div>

          <div className="drawer-field">
            <label htmlFor="filter-team">Domain / Team</label>
            <select
              id="filter-team"
              value={filters.team}
              onChange={(e) => onChangeFilters({ ...filters, team: e.target.value })}
            >
              <option value="All">All</option>
              {options.teams.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>

          <div className="drawer-field">
            <label htmlFor="filter-context">Context / Sub-Project</label>
            <select
              id="filter-context"
              value={filters.context}
              onChange={(e) => onChangeFilters({ ...filters, context: e.target.value })}
            >
              <option value="All">All</option>
              {options.contexts.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div className="drawer-field">
            <label htmlFor="filter-milestone">Milestone</label>
            <select
              id="filter-milestone"
              value={filters.milestone}
              onChange={(e) => onChangeFilters({ ...filters, milestone: e.target.value })}
            >
              <option value="All">All</option>
              {options.milestones.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>
        </section>

        <section className="drawer-section">
          <div className="drawer-section-title">
            <Calendar size={14} />
            <span>Time Range</span>
          </div>

          <div className="preset-grid">
            {(
              [
                ["30d", "30 Days"],
                ["90d", "90 Days"],
                ["1y", "1 Year"],
                ["all", "All Time"],
              ] as const
            ).map(([preset, label]) => (
              <button
                key={preset}
                type="button"
                className={`pulse-btn-secondary ${filters.preset === preset ? "active" : ""}`}
                onClick={() => applyPreset(preset)}
              >
                {label}
              </button>
            ))}
          </div>

          <div className="drawer-field">
            <label htmlFor="filter-start-date">Start Date</label>
            <input
              id="filter-start-date"
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

          <div className="drawer-field">
            <label htmlFor="filter-end-date">End Date</label>
            <input
              id="filter-end-date"
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
        </section>

        <section className="drawer-section">
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div className="drawer-section-title">
              <RefreshCw size={14} />
              <span>Sync Status</span>
            </div>
            <button
              type="button"
              className="pulse-btn-secondary"
              style={{ height: "26px", fontSize: "0.75rem", padding: "0 0.55rem" }}
              disabled={refreshing}
              onClick={onRefreshData}
            >
              {refreshing ? "Refreshing..." : "Refresh"}
            </button>
          </div>
          <div style={{ fontSize: "0.8rem", color: "var(--muted)" }}>
            <div>
              <strong style={{ color: "var(--text)" }}>Status:</strong> {syncStatus.status}
            </div>
            <div>
              <strong style={{ color: "var(--text)" }}>Last Sync:</strong> {syncStatus.last_sync}
            </div>
          </div>
        </section>

        <section className="drawer-section">
          <div className="drawer-section-title">
            <Shield size={14} />
            <span>Admin Access</span>
          </div>
          {isAdmin ? (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <span style={{ fontSize: "0.8rem", color: "var(--chart-7)" }}>Authenticated</span>
              <div style={{ display: "flex", gap: "0.5rem" }}>
                <button
                  type="button"
                  className="pulse-btn-primary"
                  style={{ flex: 1, height: "30px", fontSize: "0.78rem" }}
                  onClick={() => {
                    onClose();
                    onOpenAdminModal();
                  }}
                >
                  Open Console
                </button>
                <button
                  type="button"
                  className="pulse-btn-secondary"
                  style={{ height: "30px", fontSize: "0.78rem" }}
                  onClick={() => void onAdminLogout()}
                >
                  Logout
                </button>
              </div>
            </div>
          ) : (
            <form onSubmit={(e) => void handleLogin(e)} style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              <div className="drawer-field">
                <label htmlFor="sidebar-admin-password">Password</label>
                <input
                  id="sidebar-admin-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter admin password"
                />
              </div>
              {authError && (
                <span style={{ fontSize: "0.76rem", color: "var(--node-pink)" }}>{authError}</span>
              )}
              <button
                type="submit"
                className="pulse-btn-secondary"
                disabled={submitting || !password}
              >
                {submitting ? "Signing in..." : "Sign in"}
              </button>
            </form>
          )}
        </section>

        <div
          style={{
            marginTop: "auto",
            paddingTop: "0.4rem",
            fontSize: "0.74rem",
            color: "var(--muted)",
            fontFamily: "var(--font-mono)",
          }}
        >
          v{version}
        </div>
      </aside>
    </>
  );
}
