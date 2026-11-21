import { useEffect, useState, type KeyboardEvent } from "react";
import { Check, Copy, RotateCcw, Save } from "lucide-react";
import { ApiError, fetchRuleText, saveRuleText } from "../../lib/api";
import type { RuleProblem, RuleSaveResponse, RuleTextResponse } from "../../lib/types";

interface TextViewProps {
  name: string;
  revision: string;
  canEdit: boolean;
  dirty: boolean;
  onSaved: (res: RuleSaveResponse) => Promise<void>;
  onSessionExpired: () => void;
  onReloadLatest: () => void;
}

export function TextView({
  name,
  revision,
  canEdit,
  dirty,
  onSaved,
  onSessionExpired,
  onReloadLatest,
}: TextViewProps) {
  const [data, setData] = useState<RuleTextResponse | null>(null);
  const [value, setValue] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveProblems, setSaveProblems] = useState<RuleProblem[]>([]);
  const [conflict, setConflict] = useState(false);
  const [saving, setSaving] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "unavailable">("idle");

  useEffect(() => {
    let current = true;
    setData(null);
    setError(null);
    setSaveError(null);
    setSaveProblems([]);
    setConflict(false);
    fetchRuleText(name)
      .then((res) => {
        if (current) {
          setData(res);
          setValue(res.text);
        }
      })
      .catch((err: unknown) => {
        if (current) setError(err instanceof Error ? err.message : "Could not load the YAML file");
      });
    return () => {
      current = false;
    };
  }, [name, revision, attempt]);

  const yamlDirty = data !== null && value !== data.text;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopyState("copied");
      window.setTimeout(() => setCopyState("idle"), 2000);
    } catch {
      setCopyState("unavailable");
    }
  };

  const handleSave = async () => {
    if (!canEdit || !yamlDirty || saving) return;
    if (
      dirty &&
      !window.confirm("You have unsaved changes in the UI editor. Saving YAML will replace them. Continue?")
    ) {
      return;
    }
    setSaving(true);
    setSaveError(null);
    setSaveProblems([]);
    setConflict(false);
    try {
      const res = await saveRuleText(name, revision, value);
      await onSaved(res);
    } catch (err) {
      if (err instanceof ApiError && err.status === 422) {
        setSaveError(err.message);
        setSaveProblems(err.problems);
      } else if (err instanceof ApiError && err.status === 409) {
        setConflict(true);
        setSaveError(err.message);
      } else if (err instanceof ApiError && err.status === 401) {
        onSessionExpired();
        setSaveError("Your session has ended. Unlock editing to save.");
      } else {
        setSaveError(err instanceof Error ? err.message : "Saving YAML failed");
      }
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Tab" && canEdit && !saving) {
      e.preventDefault();
      const target = e.currentTarget;
      const start = target.selectionStart;
      const end = target.selectionEnd;
      const next = `${value.slice(0, start)}  ${value.slice(end)}`;
      setValue(next);
      window.requestAnimationFrame(() => {
        target.selectionStart = start + 2;
        target.selectionEnd = start + 2;
      });
    } else if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s") {
      e.preventDefault();
      void handleSave();
    }
  };

  if (error) {
    return (
      <div className="settings-impact-error">
        <p className="settings-error-text" role="alert">
          {error}
        </p>
        <button type="button" className="pulse-btn-secondary settings-btn-small" onClick={() => setAttempt((n) => n + 1)}>
          Try again
        </button>
      </div>
    );
  }
  if (!data) return <p className="settings-hint">Loading YAML…</p>;

  return (
    <div className="settings-rows">
      <div className="yaml-editor-meta">
        <span className="settings-hint">
          <code className="settings-code">{data.path}</code>
        </span>
        <div className="yaml-editor-actions">
          <button
            type="button"
            className="pulse-btn-secondary settings-btn-small"
            onClick={() => void copy()}
          >
            {copyState === "copied" ? <Check size={12} /> : <Copy size={12} />}
            <span>{copyState === "copied" ? "Copied" : "Copy"}</span>
          </button>
          {canEdit && yamlDirty && (
            <button
              type="button"
              className="pulse-btn-secondary settings-btn-small"
              disabled={saving}
              onClick={() => {
                setValue(data.text);
                setSaveError(null);
                setSaveProblems([]);
                setConflict(false);
              }}
            >
              <RotateCcw size={12} />
              <span>Reset</span>
            </button>
          )}
          {canEdit && (
            <button
              type="button"
              className="pulse-btn-primary settings-btn-small"
              disabled={!yamlDirty || saving}
              onClick={() => void handleSave()}
            >
              <Save size={12} />
              <span>{saving ? "Saving…" : "Save YAML"}</span>
            </button>
          )}
        </div>
      </div>

      {copyState === "unavailable" && (
        <p className="settings-hint" role="status">
          Copying is not available in this browser. Select the text instead.
        </p>
      )}

      {dirty && (
        <p className="settings-hint">
          Unsaved UI form edits are not reflected below. Saving YAML replaces them.
        </p>
      )}

      {saveError && (
        <div className={`settings-notice ${conflict ? "warning" : "error"}`} role="alert">
          <div className="edit-bar-notice-row">
            <span>{saveError}</span>
            {conflict && (
              <button
                type="button"
                className="pulse-btn-secondary settings-btn-small"
                onClick={onReloadLatest}
              >
                Reload latest
              </button>
            )}
          </div>
          {saveProblems.length > 0 && (
            <ul className="settings-problem-list">
              {saveProblems.map((p, i) => (
                <li key={i}>
                  <code>{p.path}</code>: {p.message}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <textarea
        className="settings-text-view yaml-textarea"
        aria-label="Rule set YAML editor"
        spellCheck={false}
        readOnly={!canEdit || saving}
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
          if (saveError) {
            setSaveError(null);
            setSaveProblems([]);
          }
        }}
        onKeyDown={handleKeyDown}
      />

      {canEdit && (
        <p className="settings-hint">
          Comments and formatting are preserved when saved here. Press Ctrl/Cmd+S to save &amp; apply.
        </p>
      )}
    </div>
  );
}
