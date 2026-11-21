import { Fragment } from "react";
import { SECTIONS, type SectionId } from "./sections";

interface SettingsNavProps {
  section: SectionId;
  problemCounts: Partial<Record<SectionId, number>>;
  onSelect: (id: SectionId) => void;
}

export function SettingsNav({ section, problemCounts, onSelect }: SettingsNavProps) {
  return (
    <nav className="settings-nav" aria-label="Settings sections">
      {SECTIONS.map((s, i) => {
        const count = problemCounts[s.id] ?? 0;
        const startsGroup = s.group !== undefined && SECTIONS[i - 1]?.group !== s.group;
        return (
          <Fragment key={s.id}>
            {startsGroup && (
              <>
                <div className="settings-nav-divider" role="separator" />
                <span className="settings-nav-group">{s.group}</span>
              </>
            )}
            <button
              type="button"
              className="settings-nav-item"
              aria-current={s.id === section ? "page" : undefined}
              onClick={() => onSelect(s.id)}
            >
              <span>{s.title}</span>
              {count > 0 && (
                <span className="settings-nav-badge" aria-label={`${count} problems`}>
                  {count}
                </span>
              )}
            </button>
          </Fragment>
        );
      })}
    </nav>
  );
}
