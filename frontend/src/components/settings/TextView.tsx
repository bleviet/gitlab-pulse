import { useEffect, useState } from "react";
import { fetchRuleText } from "../../lib/api";
import type { RuleTextResponse } from "../../lib/types";

interface TextViewProps {
  name: string;
  refreshKey: string;
  dirty: boolean;
}

export function TextView({ name, refreshKey, dirty }: TextViewProps) {
  const [data, setData] = useState<RuleTextResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "unavailable">("idle");

  useEffect(() => {
    let current = true;
    setData(null);
    setError(null);
    fetchRuleText(name)
      .then((res) => {
        if (current) setData(res);
      })
      .catch((err: unknown) => {
        if (current) setError(err instanceof Error ? err.message : "Could not load the text");
      });
    return () => {
      current = false;
    };
  }, [name, refreshKey, attempt]);

  const copy = async () => {
    if (!data) return;
    try {
      await navigator.clipboard.writeText(data.text);
      setCopyState("copied");
    } catch {
      setCopyState("unavailable");
    }
  };

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
  if (!data) return <p className="settings-hint">Loading…</p>;

  return (
    <div className="settings-rows">
      <p className="settings-intro-text">
        Stored at <code className="settings-code">{data.path}</code> (YAML)
      </p>
      {dirty && <p className="settings-hint">Unsaved changes are not shown here.</p>}
      <div>
        <button type="button" className="pulse-btn-secondary" onClick={() => void copy()}>
          Copy
        </button>
        <span className="settings-hint" role="status">
          {copyState === "copied" && " Copied"}
          {copyState === "unavailable" && " Copying is not available in this browser. Select the text instead."}
        </span>
      </div>
      <pre className="settings-text-view" tabIndex={0} aria-label="Stored rule set text">
        {data.text}
      </pre>
    </div>
  );
}
