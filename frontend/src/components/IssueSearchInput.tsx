import { useEffect, useMemo, useRef, useState } from "react";
import { Search, X } from "lucide-react";

interface IssueSearchInputProps {
  value: string;
  onChange: (value: string) => void;
}

export function IssueSearchInput({ value, onChange }: IssueSearchInputProps) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [focused, setFocused] = useState(false);

  const shortcut = useMemo(() => {
    const platform = typeof navigator !== "undefined" ? navigator.platform : "";
    return /Mac|iPhone|iPad/i.test(platform) ? "⌘K" : "Ctrl K";
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
        inputRef.current?.select();
      }
    };
    window.addEventListener("keydown", onKeyDown, true);
    return () => window.removeEventListener("keydown", onKeyDown, true);
  }, []);

  const expanded = focused || value.trim().length > 0;

  return (
    <div className={`pulse-search ${expanded ? "expanded" : ""}`}>
      <Search size={14} className="pulse-search-icon" aria-hidden="true" />
      <input
        ref={inputRef}
        type="text"
        value={value}
        placeholder="Search issues"
        aria-label="Search issues"
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            inputRef.current?.blur();
          }
        }}
      />
      {!expanded && (
        <kbd className="pulse-search-kbd" aria-hidden="true">
          {shortcut}
        </kbd>
      )}
      {value && (
        <button
          type="button"
          className="pulse-search-clear"
          aria-label="Clear search"
          onClick={() => {
            onChange("");
            inputRef.current?.focus();
          }}
        >
          <X size={13} />
        </button>
      )}
    </div>
  );
}
