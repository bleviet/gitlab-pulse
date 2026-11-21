import { useEffect, useRef, useState } from "react";
import type { ProjectInfo } from "../../lib/projectInventory";
import { problemsByPath, teamNameInUse } from "../../lib/ruleDraft";
import type { RuleProblem } from "../../lib/types";
import { ProjectChecklist } from "./ProjectChecklist";
import { TextField } from "./TextField";

interface NewRuleSetDialogProps {
  projects: ProjectInfo[];
  claimedBy: Record<number, string>;
  sourceLabel: string;
  teamNames: string[];
  busy: boolean;
  problems: RuleProblem[];
  error: string | null;
  onCreate: (team: string, projectIds: number[]) => void;
  onClose: () => void;
}

export function NewRuleSetDialog({
  projects,
  claimedBy,
  sourceLabel,
  teamNames,
  busy,
  problems,
  error,
  onCreate,
  onClose,
}: NewRuleSetDialogProps) {
  const [team, setTeam] = useState("");
  const [ids, setIds] = useState<number[]>([]);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const lookup = problemsByPath(problems);

  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    dialogRef.current?.querySelector<HTMLInputElement>("input")?.focus();
    return () => opener?.focus();
  }, []);

  const otherProblems = problems.filter((p) => p.path !== "team" && p.path !== "project_ids");

  const known = [...projects];
  for (const id of ids) {
    if (!known.some((p) => p.id === id)) known.push({ id, name: `Project ${id}`, count: 0 });
  }

  return (
    <div className="settings-modal-backdrop">
      <div
        ref={dialogRef}
        className="settings-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-new-title"
        onKeyDown={(e) => {
          if (e.key === "Escape" && !busy) {
            e.preventDefault();
            e.stopPropagation();
            onClose();
          }
        }}
      >
        <h3 id="settings-new-title" className="settings-section-title">
          New rule set
        </h3>
        <p className="settings-hint">
          The new rule set starts as a copy of {sourceLabel}.
        </p>
        <TextField
          id="settings-new-team"
          label="Team name"
          value={team}
          problem={lookup["team"]}
          hint={
            teamNameInUse(team, teamNames)
              ? "Another rule set uses this team name. The dashboard will show both as one team."
              : undefined
          }
          onChange={setTeam}
        />
        <ProjectChecklist
          idBase="settings-new-projects"
          projects={known}
          selected={ids}
          claimedBy={claimedBy}
          problem={lookup["project_ids"]}
          onChange={setIds}
        />
        {otherProblems.length > 0 && (
          <div role="alert">
            <p className="settings-error-text">The rule set you are copying has problems:</p>
            <ul className="settings-problem-list settings-error-text">
              {otherProblems.map((p, i) => (
                <li key={i}>{p.message}</li>
              ))}
            </ul>
          </div>
        )}
        {error && otherProblems.length === 0 && (
          <p className="settings-error-text" role="alert">
            {error}
          </p>
        )}
        <div className="settings-modal-actions">
          <button type="button" className="pulse-btn-secondary" disabled={busy} onClick={onClose}>
            Cancel
          </button>
          <button
            type="button"
            className="pulse-btn-primary"
            disabled={busy || team.trim() === "" || ids.length === 0}
            onClick={() => onCreate(team, ids)}
          >
            {busy ? "Creating…" : "Create"}
          </button>
        </div>
      </div>
    </div>
  );
}
