import { teamNameInUse } from "../../lib/ruleDraft";
import { knownProjects, type ProjectInfo } from "../../lib/projectInventory";
import type { RuleSetBody } from "../../lib/types";
import { ProjectChecklist } from "./ProjectChecklist";
import { TextField } from "./TextField";

interface ProjectsEditorProps {
  rule: RuleSetBody;
  isDefault: boolean;
  hasDefault: boolean;
  otherTeamNames: string[];
  inventory: ProjectInfo[];
  claimedBy: Record<number, string>;
  problems: Record<string, string>;
  deleteBlocked: boolean;
  deleting: boolean;
  onChange: (next: RuleSetBody) => void;
  onDelete: () => void;
}

export function ProjectsEditor({
  rule,
  isDefault,
  hasDefault,
  otherTeamNames,
  inventory,
  claimedBy,
  problems,
  deleteBlocked,
  deleting,
  onChange,
  onDelete,
}: ProjectsEditorProps) {
  const remaining = inventory.filter((p) => claimedBy[p.id] === undefined);
  const all = knownProjects(
    inventory,
    [],
    [...rule.project_ids, ...Object.keys(claimedBy).map(Number)],
  );

  return (
    <div className="settings-rows">
      {!hasDefault && (
        <div className="settings-notice warning" role="status">
          No rule set covers the remaining projects. Projects that are not ticked anywhere are
          shown without types and stages.
        </div>
      )}
      {!isDefault && rule.project_ids.length === 0 && (
        <div className="settings-notice warning" role="status">
          This rule set has no projects, so it is not used. Tick its projects, or delete it.
        </div>
      )}
      <div className="settings-row">
        <TextField
          id="settings-team"
          label="Team name"
          value={rule.team}
          problem={problems["team"]}
          hint={
            teamNameInUse(rule.team, otherTeamNames)
              ? "Another rule set uses this team name. The dashboard will show both as one team."
              : undefined
          }
          onChange={(team) => onChange({ ...rule, team })}
        />
        <p className="settings-hint">
          The team name is shown in the dashboard&apos;s team filter.
        </p>
      </div>

      <div className="settings-row">
        {isDefault ? (
          <>
            <p className="settings-intro-text">
              These rules apply to every project that has no rule set of its own.
            </p>
            <ul className="settings-project-readonly">
              {remaining.length === 0 && (
                <li className="settings-hint">No projects fall under these rules right now.</li>
              )}
              {remaining.map((p) => (
                <li key={p.id} className="settings-project">
                  <span className="settings-project-name">{p.name}</span>
                  <span className="settings-project-meta">
                    {p.count} {p.count === 1 ? "issue" : "issues"}
                  </span>
                </li>
              ))}
            </ul>
          </>
        ) : (
          <ProjectChecklist
            idBase="settings-projects"
            projects={all}
            selected={rule.project_ids}
            claimedBy={claimedBy}
            problem={problems["project_ids"]}
            onChange={(project_ids) => onChange({ ...rule, project_ids })}
          />
        )}
      </div>

      {!isDefault && (
        <div className="settings-danger">
          <h4 className="settings-row-title">Delete this rule set</h4>
          <p className="settings-hint">
            Its projects will use the default rules. Deleting is applied immediately.
          </p>
          <button
            type="button"
            className="pulse-btn-secondary settings-danger-btn"
            aria-describedby={deleteBlocked ? "settings-delete-hint" : undefined}
            disabled={deleteBlocked || deleting}
            onClick={onDelete}
          >
            {deleting ? "Deleting…" : "Delete this rule set"}
          </button>
          {deleteBlocked && (
            <p id="settings-delete-hint" className="settings-hint">
              Save or discard your changes first.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
