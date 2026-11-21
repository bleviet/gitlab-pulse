import { useCallback, useEffect, useState } from "react";
import { fetchRuleVersion, fetchRuleVersions } from "../../lib/api";
import type { RuleSetBody, RuleVersionEntry } from "../../lib/types";

const formatter = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" });

function describe(entry: RuleVersionEntry): string {
  if (entry.kind === "template" || !entry.saved_at) return "Version shipped with GitLab Pulse";
  return `Version used until ${formatter.format(new Date(entry.saved_at))}`;
}

interface HistoryPanelProps {
  name: string;
  refreshKey: string;
  canEdit: boolean;
  dirty: boolean;
  onLoadVersion: (rule: RuleSetBody, description: string) => void;
}

export function HistoryPanel({ name, refreshKey, canEdit, dirty, onLoadVersion }: HistoryPanelProps) {
  const [versions, setVersions] = useState<RuleVersionEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (!canEdit) return;
    let current = true;
    setVersions(null);
    setError(null);
    fetchRuleVersions(name)
      .then((res) => {
        if (current) setVersions(res.versions);
      })
      .catch((err: unknown) => {
        if (current) setError(err instanceof Error ? err.message : "Could not load earlier versions");
      });
    return () => {
      current = false;
    };
  }, [name, refreshKey, canEdit, attempt]);

  const handleLoad = useCallback(
    async (entry: RuleVersionEntry) => {
      if (dirty && !window.confirm("Replace your unsaved changes with this version?")) return;
      setLoadingId(entry.id);
      setActionError(null);
      try {
        const res = await fetchRuleVersion(name, entry.id);
        const text =
          entry.kind === "template" || !entry.saved_at
            ? "Loaded the version shipped with GitLab Pulse."
            : `Loaded the version used until ${formatter.format(new Date(entry.saved_at))}.`;
        onLoadVersion(res.rule, `${text} Check the effect, then choose Save & apply to make it current.`);
      } catch (err) {
        setActionError(err instanceof Error ? err.message : "Could not load this version");
      } finally {
        setLoadingId(null);
      }
    },
    [dirty, name, onLoadVersion],
  );

  if (!canEdit) {
    return <p className="settings-hint">Unlock editing to load an earlier version.</p>;
  }
  if (error) {
    return (
      <div className="settings-impact-error">
        <p className="settings-error-text" role="alert">
          {error}
        </p>
        <button type="button" className="pulse-btn-secondary" onClick={() => setAttempt((n) => n + 1)}>
          Try again
        </button>
      </div>
    );
  }
  if (versions === null) return <p className="settings-hint">Loading earlier versions…</p>;
  if (versions.length === 0) {
    return (
      <p className="settings-hint">
        No earlier versions yet. A version is kept every time you save.
      </p>
    );
  }

  return (
    <div className="settings-rows">
      <ul className="settings-version-list">
        {versions.map((entry) => (
          <li key={entry.id} className="settings-version">
            <span>{describe(entry)}</span>
            <button
              type="button"
              className="pulse-btn-secondary"
              disabled={loadingId !== null}
              onClick={() => void handleLoad(entry)}
            >
              {loadingId === entry.id ? "Loading…" : "Load into editor"}
            </button>
          </li>
        ))}
      </ul>
      <p className="settings-hint">Team name and projects stay as they are now. Everything else, including colours, comes from the version you load.</p>
      {actionError && (
        <p className="settings-error-text" role="alert">
          {actionError}
        </p>
      )}
    </div>
  );
}
