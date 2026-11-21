import { useEffect, useRef, useState } from "react";
import {
  ChevronDown,
  Code2,
  FolderKanban,
  History,
  Lock,
  LockOpen,
  Palette,
  Plus,
  RotateCcw,
  Save,
  X,
} from "lucide-react";
import type { RuleSetItem, SectionId } from "../../lib/types";
import type { Notice } from "./saveFlow";
import type { ActiveRulePopover, MixSubTab, RulePopoverId } from "./useRuleEditor";

interface EditModeBarProps {
  loadState: "loading" | "error" | "ready";
  loadError: string | null;
  chartsVisible: boolean;
  ruleSets: RuleSetItem[];
  selected: RuleSetItem | null;
  defaultName: string | null;
  dirty: boolean;
  saving: boolean;
  problemCount: number;
  problemCountBySection: Partial<Record<SectionId, number>>;
  unplacedProblems: string[];
  loadErrorNotice: string | null;
  notice: Notice | null;
  activePopover: ActiveRulePopover | null;
  onRetryLoad: () => void;
  onSelectRuleSet: (name: string) => void;
  onOpenPopover: (
    id: RulePopoverId,
    anchor: HTMLElement | null,
    placement?: "right" | "bottom",
    subTab?: MixSubTab,
  ) => void;
  onNewRuleSet: () => void;
  onDiscard: () => void;
  onSave: () => void;
  onDismissNotice: () => void;
  onReloadLatest: () => void;
  onLock: () => void;
}

function optionText(item: RuleSetItem, isDefault: boolean): string {
  const count = item.rule.project_ids.length;
  const team = item.rule.team || item.name;
  if (isDefault) return `${team} (default)`;
  if (count === 0) return `${team} (no projects)`;
  return `${team} (${count} ${count === 1 ? "project" : "projects"})`;
}

export function EditModeBar({
  loadState,
  loadError,
  chartsVisible,
  ruleSets,
  selected,
  defaultName,
  dirty,
  saving,
  problemCount,
  problemCountBySection,
  unplacedProblems,
  loadErrorNotice,
  notice,
  activePopover,
  onRetryLoad,
  onSelectRuleSet,
  onOpenPopover,
  onNewRuleSet,
  onDiscard,
  onSave,
  onDismissNotice,
  onReloadLatest,
  onLock,
}: EditModeBarProps) {
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement | null>(null);
  const moreBtnRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!moreOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) {
        setMoreOpen(false);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        setMoreOpen(false);
      }
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [moreOpen]);

  const mixProblems =
    (problemCountBySection.priority ?? 0) + (problemCountBySection.type ?? 0);
  const colorProblems = problemCountBySection.colors ?? 0;

  const chip = (
    id: RulePopoverId,
    label: string,
    problems = 0,
    subTab?: MixSubTab,
  ) => {
    const active = activePopover?.id === id;
    return (
      <button
        key={id}
        type="button"
        data-rule-trigger={id}
        className={`edit-bar-chip${active ? " active" : ""}${problems > 0 ? " has-error" : ""}`}
        aria-expanded={active}
        onClick={(e) => onOpenPopover(id, e.currentTarget, "bottom", subTab)}
      >
        <span>{label}</span>
        {problems > 0 && <span className="edit-bar-badge">{problems}</span>}
      </button>
    );
  };

  let statusText = "";
  let statusError = false;
  if (saving) statusText = "Saving & recalculating…";
  else if (problemCount > 0) {
    statusText = `${problemCount} ${problemCount === 1 ? "problem" : "problems"}`;
    statusError = true;
  } else if (dirty) {
    statusText = "Unsaved changes";
  }

  return (
    <div className="edit-mode-bar" role="region" aria-label="Rule edit mode">
      <div className="edit-mode-bar-main">
        <div className="edit-mode-bar-left">
          <span className="edit-mode-pill">
            <LockOpen size={12} aria-hidden="true" />
            <span>Edit mode</span>
          </span>

          {loadState === "loading" && <span className="edit-bar-status">Loading rules…</span>}

          {loadState === "error" && (
            <span className="edit-bar-status error">
              {loadError ?? "Failed to load rules"}
              <button type="button" className="edit-bar-chip" onClick={onRetryLoad}>
                Retry
              </button>
            </span>
          )}

          {loadState === "ready" && selected && (
            <>
              {ruleSets.length > 1 ? (
                <select
                  aria-label="Rule set"
                  className="edit-bar-select"
                  value={selected.name}
                  disabled={saving}
                  onChange={(e) => onSelectRuleSet(e.target.value)}
                >
                  {ruleSets.map((r) => (
                    <option key={r.name} value={r.name}>
                      {optionText(r, r.name === defaultName)}
                    </option>
                  ))}
                </select>
              ) : (
                <span className="edit-bar-hint">
                  Click <strong>Edit</strong> on any panel, or pick a rule below:
                </span>
              )}

              <div className="edit-bar-chips" role="group" aria-label="Rule editors">
                {!chartsVisible && chip("mix", "Types & Priority", mixProblems, "priority")}
                {!chartsVisible && chip("stages", "Stages", problemCountBySection.stages ?? 0)}
                {!chartsVisible && chip("quality", "Quality", problemCountBySection.quality ?? 0)}
                {chip("impact", "Impact", problemCountBySection.impact ?? 0)}
                {chip("contexts", "Contexts", problemCountBySection.contexts ?? 0)}
                {chip("projects", "Projects", problemCountBySection.projects ?? 0)}
                {chip("text", "YAML")}

                <div ref={moreRef} className="edit-bar-more">
                  <button
                    ref={moreBtnRef}
                    type="button"
                    data-rule-trigger="more"
                    className={`edit-bar-chip${moreOpen || activePopover?.id === "colors" || activePopover?.id === "history" ? " active" : ""}${colorProblems > 0 ? " has-error" : ""}`}
                    aria-expanded={moreOpen}
                    aria-haspopup="menu"
                    onClick={() => setMoreOpen((v) => !v)}
                  >
                    <span>More</span>
                    {colorProblems > 0 && <span className="edit-bar-badge">{colorProblems}</span>}
                    <ChevronDown size={12} aria-hidden="true" />
                  </button>

                  {moreOpen && (
                    <div className="edit-bar-menu" role="menu">
                      <button
                        type="button"
                        role="menuitem"
                        className="edit-bar-menu-item"
                        onClick={() => {
                          setMoreOpen(false);
                          onOpenPopover("colors", moreBtnRef.current, "bottom");
                        }}
                      >
                        <Palette size={13} aria-hidden="true" />
                        <span>Rule colours</span>
                        {colorProblems > 0 && (
                          <span className="edit-bar-badge">{colorProblems}</span>
                        )}
                      </button>
                      <button
                        type="button"
                        role="menuitem"
                        className="edit-bar-menu-item"
                        disabled={dirty || saving}
                        title={dirty ? "Save or discard changes first" : undefined}
                        onClick={() => {
                          setMoreOpen(false);
                          onNewRuleSet();
                        }}
                      >
                        <Plus size={13} aria-hidden="true" />
                        <span>New team rule set</span>
                      </button>
                      <div className="edit-bar-menu-divider" role="separator" />
                      <button
                        type="button"
                        role="menuitem"
                        className="edit-bar-menu-item"
                        onClick={() => {
                          setMoreOpen(false);
                          onOpenPopover("history", moreBtnRef.current, "bottom");
                        }}
                      >
                        <History size={13} aria-hidden="true" />
                        <span>Earlier versions</span>
                      </button>
                      <button
                        type="button"
                        role="menuitem"
                        className="edit-bar-menu-item"
                        onClick={() => {
                          setMoreOpen(false);
                          onOpenPopover("text", moreBtnRef.current, "bottom");
                        }}
                      >
                        <Code2 size={13} aria-hidden="true" />
                        <span>Edit YAML</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        <div className="edit-mode-bar-right">
          {statusText && (
            <span
              className={`edit-bar-status${statusError ? " error" : ""}`}
              role="status"
              aria-live="polite"
            >
              {statusText}
            </span>
          )}

          {dirty && (
            <button
              type="button"
              className="pulse-btn-secondary edit-bar-btn"
              disabled={saving}
              onClick={onDiscard}
            >
              <RotateCcw size={12} aria-hidden="true" />
              <span>Discard</span>
            </button>
          )}

          <button
            type="button"
            className="pulse-btn-primary edit-bar-btn"
            disabled={!dirty || saving || problemCount > 0 || loadState !== "ready"}
            onClick={onSave}
          >
            <Save size={12} aria-hidden="true" />
            <span>{saving ? "Saving…" : "Save & apply"}</span>
          </button>

          <button
            type="button"
            className="pulse-btn-secondary edit-bar-btn"
            disabled={saving}
            onClick={onLock}
            title="Lock and exit edit mode"
          >
            <Lock size={12} aria-hidden="true" />
            <span>Lock</span>
          </button>
        </div>
      </div>

      {(notice || loadErrorNotice || unplacedProblems.length > 0) && (
        <div className="edit-mode-bar-notices">
          {loadErrorNotice && (
            <div className="edit-bar-notice warning" role="status">
              <FolderKanban size={13} aria-hidden="true" />
              <span>{loadErrorNotice}</span>
            </div>
          )}
          {unplacedProblems.length > 0 && (
            <div className="edit-bar-notice error" role="alert">
              <span>{unplacedProblems.join(" · ")}</span>
            </div>
          )}
          {notice && (
            <div
              className={`edit-bar-notice ${notice.kind === "conflict" ? "warning" : notice.kind}`}
              role={notice.kind === "success" || notice.kind === "info" ? "status" : "alert"}
            >
              <div className="edit-bar-notice-row">
                <span>{notice.text}</span>
                {notice.kind === "conflict" && (
                  <button
                    type="button"
                    className="pulse-btn-secondary edit-bar-btn"
                    onClick={onReloadLatest}
                  >
                    Reload latest
                  </button>
                )}
                <button
                  type="button"
                  className="pulse-icon-btn rule-popover-close"
                  aria-label="Dismiss notice"
                  onClick={onDismissNotice}
                >
                  <X size={12} />
                </button>
              </div>
              {notice.job?.stdout && <pre className="admin-log">{notice.job.stdout}</pre>}
              {notice.job?.stderr && <pre className="admin-log">{notice.job.stderr}</pre>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
