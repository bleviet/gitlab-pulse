import { ArrowDown, ArrowUp, Trash2 } from "lucide-react";

interface RowControlsProps {
  label: string;
  index: number;
  count: number;
  onMove?: (delta: number) => void;
  onRemove: () => void;
}

export function RowControls({ label, index, count, onMove, onRemove }: RowControlsProps) {
  const name = label.trim() || "item";
  return (
    <div className="settings-row-controls">
      {onMove && (
        <>
          <button
            type="button"
            className="pulse-icon-btn"
            aria-label={`Move ${name} up`}
            title="Move up"
            disabled={index === 0}
            onClick={() => onMove(-1)}
          >
            <ArrowUp size={14} />
          </button>
          <button
            type="button"
            className="pulse-icon-btn"
            aria-label={`Move ${name} down`}
            title="Move down"
            disabled={index === count - 1}
            onClick={() => onMove(1)}
          >
            <ArrowDown size={14} />
          </button>
        </>
      )}
      <button
        type="button"
        className="pulse-icon-btn settings-remove-btn"
        aria-label={`Remove ${name}`}
        title="Remove"
        onClick={onRemove}
      >
        <Trash2 size={14} />
      </button>
    </div>
  );
}
