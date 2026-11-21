import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { RotateCcw } from "lucide-react";
import {
  canReset,
  effectiveColor,
  isOverridden,
  normalizeHex,
  type ColorMap,
  type ColorTheme,
} from "../../lib/ruleColors";
import type { PaletteDefaults } from "../../lib/types";

interface ColorCellProps {
  idBase: string;
  theme: ColorTheme;
  name: string;
  colorKey: string;
  hasDefault: boolean;
  colors: ColorMap;
  defaults: PaletteDefaults;
  problem?: string;
  onSet: (hex: string) => void;
  onReset: () => void;
}

export function ColorCell({
  idBase,
  theme,
  name,
  colorKey,
  hasDefault,
  colors,
  defaults,
  problem,
  onSet,
  onReset,
}: ColorCellProps) {
  const current = effectiveColor(colors, defaults, theme, colorKey);
  const overridden = isOverridden(colors, theme, colorKey);
  const [text, setText] = useState(current ?? "");
  const [focused, setFocused] = useState(false);

  const focusedRef = useRef(false);

  useEffect(() => {
    if (!focusedRef.current) setText(current ?? "");
  }, [current]);

  const commitShort = () => {
    const hex = normalizeHex(text);
    if (!hex) return;
    setText(hex);
    if (hex !== normalizeHex(current ?? "")) onSet(hex);
  };

  const themeLabel = theme === "light" ? "light" : "dark";
  const invalid = !focused && text !== "" && normalizeHex(text) === null;
  const message = invalid ? "Enter a colour like #1a2b3c." : problem;
  const messageId = `${idBase}-problem`;

  if (!hasDefault && !overridden) {
    const start = effectiveColor(colors, defaults, theme, "primary");
    return (
      <div className="settings-color-cell">
        <span className="settings-hint">Automatic</span>
        <button
          type="button"
          className="pulse-btn-secondary settings-btn-small"
          aria-label={`Choose a colour for ${name} in the ${themeLabel} theme`}
          disabled={start === null}
          onClick={() => start && onSet(start)}
        >
          Choose
        </button>
      </div>
    );
  }

  return (
    <div className="settings-color-cell">
      <input
        type="color"
        className="settings-color-picker"
        aria-label={`${name} colour for the ${themeLabel} theme`}
        value={normalizeHex(current ?? "") ?? "#000000"}
        onChange={(e) => onSet(e.target.value)}
      />
      <input
        type="text"
        className={`settings-input settings-color-hex${message ? " error" : ""}`}
        aria-label={`${name} colour code for the ${themeLabel} theme`}
        aria-invalid={message ? true : undefined}
        aria-describedby={message ? messageId : undefined}
        value={text}
        maxLength={7}
        onFocus={() => {
          focusedRef.current = true;
          setFocused(true);
        }}
        onBlur={() => {
          focusedRef.current = false;
          commitShort();
          setFocused(false);
        }}
        onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
          if (e.key === "Enter") {
            e.preventDefault();
            commitShort();
          }
        }}
        onChange={(e) => {
          setText(e.target.value);
          if (/^#[0-9a-f]{6}$/i.test(e.target.value.trim())) {
            const hex = normalizeHex(e.target.value);
            if (hex && hex !== normalizeHex(current ?? "")) onSet(hex);
          }
        }}
      />
      <span
        className="settings-color-chip"
        data-theme={theme}
        style={current ? { color: current } : undefined}
        aria-hidden="true"
      >
        Aa
      </span>
      <button
        type="button"
        className="pulse-icon-btn"
        aria-label={`Reset ${name} for the ${themeLabel} theme to the brand colour`}
        title="Reset to the brand colour"
        disabled={!canReset(colors, defaults, theme, colorKey)}
        onClick={onReset}
      >
        <RotateCcw size={13} />
      </button>
      {message && (
        <p id={messageId} className="settings-error-text settings-color-error" role="alert">
          {message}
        </p>
      )}
    </div>
  );
}
