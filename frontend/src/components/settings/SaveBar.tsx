interface SaveBarProps {
  dirty: boolean;
  isAdmin: boolean;
  saving: boolean;
  problemCount: number;
  onDiscard: () => void;
  onSave: () => void;
}

export function SaveBar({
  dirty,
  isAdmin,
  saving,
  problemCount,
  onDiscard,
  onSave,
}: SaveBarProps) {
  let status = "";
  if (saving) status = "Saving and recalculating…";
  else if (problemCount > 0 && dirty) {
    status = `Fix ${problemCount} ${problemCount === 1 ? "problem" : "problems"} to save`;
  } else if (dirty) status = "Unsaved changes";

  return (
    <div className="settings-savebar">
      <span
        className={`settings-savebar-status${problemCount > 0 && dirty ? " error" : ""}`}
        role="status"
        aria-live="polite"
      >
        {status}
      </span>
      <button
        type="button"
        className="pulse-btn-secondary"
        disabled={!dirty || saving}
        onClick={onDiscard}
      >
        Discard
      </button>
      <button
        type="button"
        className="pulse-btn-primary"
        disabled={!dirty || !isAdmin || saving || problemCount > 0}
        onClick={onSave}
      >
        Save &amp; apply
      </button>
    </div>
  );
}
