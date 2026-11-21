import { useState } from "react";
import type { ProjectInfo } from "../../lib/projectInventory";

interface ProjectChecklistProps {
  idBase: string;
  projects: ProjectInfo[];
  selected: number[];
  claimedBy: Record<number, string>;
  onChange: (ids: number[]) => void;
  problem?: string;
}

export function ProjectChecklist({
  idBase,
  projects,
  selected,
  claimedBy,
  onChange,
  problem,
}: ProjectChecklistProps) {
  const [extra, setExtra] = useState("");
  const extraNumber = Number(extra);
  const extraValid = Number.isInteger(extraNumber) && extraNumber > 0;
  const problemId = `${idBase}-problem`;

  const toggle = (id: number, checked: boolean) => {
    onChange(checked ? [...selected, id] : selected.filter((p) => p !== id));
  };

  const addExtra = () => {
    if (!extraValid) return;
    if (!selected.includes(extraNumber)) onChange([...selected, extraNumber]);
    setExtra("");
  };

  return (
    <div className="settings-field">
      <fieldset
        className="settings-fields-group settings-project-list"
        aria-describedby={problem ? problemId : undefined}
      >
        <legend className="settings-field-label">Projects</legend>
        {projects.length === 0 && <p className="settings-hint">No projects found yet.</p>}
        {projects.map((project) => {
          const owner = claimedBy[project.id];
          const checked = selected.includes(project.id);
          return (
            <label key={project.id} className="settings-check settings-project">
              <input
                type="checkbox"
                checked={checked}
                disabled={owner !== undefined && !checked}
                onChange={(e) => toggle(project.id, e.target.checked)}
              />
              <span className="settings-project-name">{project.name}</span>
              <span className="settings-project-meta">
                {owner !== undefined
                  ? `used by ${owner}`
                  : `${project.count} ${project.count === 1 ? "issue" : "issues"}`}
              </span>
            </label>
          );
        })}
      </fieldset>

      <div className="settings-inline-form">
        <label htmlFor={`${idBase}-extra`} className="settings-visually-hidden">
          Add a project by its number
        </label>
        <input
          id={`${idBase}-extra`}
          type="number"
          min={1}
          step={1}
          className="settings-input"
          placeholder="Add a project by its number"
          value={extra}
          onChange={(e) => setExtra(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addExtra();
            }
          }}
        />
        <button
          type="button"
          className="pulse-btn-secondary settings-btn-small"
          disabled={!extraValid}
          onClick={addExtra}
        >
          Add
        </button>
      </div>

      {problem && (
        <p id={problemId} className="settings-error-text" role="alert">
          {problem}
        </p>
      )}
    </div>
  );
}
