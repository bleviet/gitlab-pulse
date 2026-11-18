import { useEffect, useState, type FormEvent } from "react";
import { Play, RefreshCw, Shield, X } from "lucide-react";
import { clearDashboardCache, runCollector, runProcessor } from "../lib/api";
import type { AdminJobResponse } from "../lib/types";

interface AdminModalProps {
  open: boolean;
  isAdmin: boolean;
  onClose: () => void;
  onLogin: (password: string) => Promise<void>;
  onLogout: () => Promise<void>;
  onReloadDashboard: () => Promise<void>;
}

export function AdminModal({
  open,
  isAdmin,
  onClose,
  onLogin,
  onLogout,
  onReloadDashboard,
}: AdminModalProps) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busyStep, setBusyStep] = useState<string | null>(null);
  const [lastJob, setLastJob] = useState<AdminJobResponse | null>(null);
  const [cacheNotice, setCacheNotice] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    if (!password) return;
    setBusyStep("login");
    setError(null);
    try {
      await onLogin(password);
      setPassword("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusyStep(null);
    }
  };

  const handleRun = async (label: string, runner: () => Promise<AdminJobResponse>) => {
    setBusyStep(label);
    setError(null);
    setCacheNotice(null);
    try {
      const res = await runner();
      setLastJob(res);
      if (res.success) {
        await onReloadDashboard();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to run ${label}`);
    } finally {
      setBusyStep(null);
    }
  };

  const handleClearCache = async () => {
    setBusyStep("cache");
    setError(null);
    setCacheNotice(null);
    try {
      await clearDashboardCache();
      await onReloadDashboard();
      setCacheNotice("Server cache cleared and dashboard data reloaded.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to clear cache");
    } finally {
      setBusyStep(null);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-label="Admin Operations"
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Shield size={18} color="var(--brand)" />
            <h2 style={{ fontSize: "1.15rem" }}>Admin Operations</h2>
          </div>
          <button type="button" className="pulse-icon-btn" aria-label="Close modal" onClick={onClose}>
            <X size={15} />
          </button>
        </div>

        {!isAdmin ? (
          <form
            onSubmit={(e) => void handleLogin(e)}
            style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}
          >
            <p style={{ margin: 0, color: "var(--muted)", fontSize: "0.86rem" }}>
              Authenticate with the dashboard admin password to trigger Layer 1 collection, Layer 2
              processing, or server cache invalidation.
            </p>
            <div className="drawer-field">
              <label htmlFor="modal-admin-password">Admin Password</label>
              <input
                id="modal-admin-password"
                type="password"
                autoFocus
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
              />
            </div>
            {error && <span style={{ color: "var(--node-pink)", fontSize: "0.82rem" }}>{error}</span>}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
              <button type="button" className="pulse-btn-secondary" onClick={onClose}>
                Cancel
              </button>
              <button
                type="submit"
                className="pulse-btn-primary"
                disabled={busyStep === "login" || !password}
              >
                {busyStep === "login" ? "Signing in..." : "Authenticate"}
              </button>
            </div>
          </form>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.9rem" }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "0.6rem" }}>
              <button
                type="button"
                className="pulse-btn-primary"
                disabled={busyStep !== null}
                onClick={() => void handleRun("Collector", runCollector)}
              >
                <Play size={14} />
                <span>{busyStep === "Collector" ? "Running Collector..." : "Run Collector (L1)"}</span>
              </button>
              <button
                type="button"
                className="pulse-btn-primary"
                disabled={busyStep !== null}
                onClick={() => void handleRun("Processor", runProcessor)}
              >
                <Play size={14} />
                <span>{busyStep === "Processor" ? "Running Processor..." : "Run Processor (L2)"}</span>
              </button>
              <button
                type="button"
                className="pulse-btn-secondary"
                disabled={busyStep !== null}
                onClick={() => void handleClearCache()}
              >
                <RefreshCw size={14} />
                <span>{busyStep === "cache" ? "Clearing..." : "Clear Cache & Reload"}</span>
              </button>
              <button
                type="button"
                className="pulse-btn-secondary"
                style={{ marginLeft: "auto" }}
                disabled={busyStep !== null}
                onClick={() => void onLogout()}
              >
                Logout
              </button>
            </div>

            {error && (
              <div style={{ color: "var(--node-pink)", fontSize: "0.84rem" }}>{error}</div>
            )}
            {cacheNotice && (
              <div style={{ color: "var(--chart-7)", fontSize: "0.84rem" }}>{cacheNotice}</div>
            )}

            {lastJob && (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div style={{ fontSize: "0.84rem", fontWeight: 700 }}>
                  {lastJob.step}:{" "}
                  <span style={{ color: lastJob.success ? "var(--chart-7)" : "var(--node-pink)" }}>
                    {lastJob.success
                      ? "Completed successfully"
                      : `Failed (exit code ${lastJob.returncode})`}
                  </span>
                </div>
                {lastJob.stdout && <pre className="admin-log">{lastJob.stdout}</pre>}
                {lastJob.stderr && <pre className="admin-log">{lastJob.stderr}</pre>}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
