import { useEffect, useRef, useState } from "react";
import { Check, Moon, Palette, Sun, X } from "lucide-react";
import { getUiTheme, UI_THEMES, type UiThemeId } from "../lib/uiThemes";
import type { ThemeMode } from "../lib/types";

interface ThemePickerProps {
  mode: ThemeMode;
  colorTheme: UiThemeId;
  onChangeMode: (mode: ThemeMode) => void;
  onChangeColorTheme: (themeId: UiThemeId) => void;
}

export function ThemePicker({
  mode,
  colorTheme,
  onChangeMode,
  onChangeColorTheme,
}: ThemePickerProps) {
  const [open, setOpen] = useState(false);
  const anchorRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (e: PointerEvent) => {
      if (anchorRef.current && !anchorRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const current = getUiTheme(colorTheme);
  const currentPreview = current.preview[mode];
  const variantLabel = mode === "dark" ? current.darkLabel : current.lightLabel;

  return (
    <div ref={anchorRef} className="theme-picker-anchor">
      <button
        type="button"
        className={`pulse-icon-btn pulse-toggle-btn${open ? " active" : ""}`}
        aria-expanded={open}
        aria-haspopup="dialog"
        aria-label={`Appearance: ${current.name} ${variantLabel}`}
        title={`Theme: ${current.name} (${variantLabel}) — personal setting`}
        onClick={() => setOpen((v) => !v)}
      >
        <span
          className="theme-picker-dot"
          style={{ background: currentPreview.accent, borderColor: currentPreview.bg }}
          aria-hidden="true"
        />
        <Palette size={14} aria-hidden="true" />
      </button>

      {open && (
        <div
          className="scope-popover theme-picker-popover"
          role="dialog"
          aria-label="Appearance and color themes"
        >
          <div className="scope-popover-head">
            <span className="pulse-panel-title">Appearance</span>
            <div className="pulse-segmented compact" role="group" aria-label="Color mode">
              <button
                type="button"
                aria-pressed={mode === "dark"}
                onClick={() => onChangeMode("dark")}
              >
                <Moon size={11} aria-hidden="true" />
                <span>Dark</span>
              </button>
              <button
                type="button"
                aria-pressed={mode === "light"}
                onClick={() => onChangeMode("light")}
              >
                <Sun size={11} aria-hidden="true" />
                <span>Light</span>
              </button>
            </div>
            <button
              type="button"
              className="pulse-icon-btn rule-popover-close"
              aria-label="Close appearance"
              onClick={() => setOpen(false)}
            >
              <X size={12} />
            </button>
          </div>

          <div className="theme-picker-grid" role="group" aria-label="Color themes">
            {UI_THEMES.map((item) => {
              const preview = item.preview[mode];
              const isSelected = item.id === colorTheme;
              const sub = mode === "dark" ? item.darkLabel : item.lightLabel;
              return (
                <button
                  key={item.id}
                  type="button"
                  className={`theme-choice-card${isSelected ? " active" : ""}`}
                  aria-pressed={isSelected}
                  style={{
                    background: preview.bg,
                    color: preview.text,
                    borderColor: isSelected ? preview.accent : undefined,
                  }}
                  onClick={() => onChangeColorTheme(item.id)}
                >
                  <div
                    className="theme-choice-surface"
                    style={{ background: preview.card }}
                  >
                    <div className="theme-choice-head">
                      <span className="theme-choice-name" style={{ color: preview.text }}>
                        {item.name}
                      </span>
                      {isSelected && (
                        <span
                          className="theme-choice-check"
                          style={{ background: preview.accent, color: preview.bg }}
                          aria-hidden="true"
                        >
                          <Check size={10} strokeWidth={3} />
                        </span>
                      )}
                    </div>
                    <span className="theme-choice-variant">{sub}</span>
                    <div className="theme-choice-swatches" aria-hidden="true">
                      {preview.swatches.map((hex, i) => (
                        <span
                          key={i}
                          className="theme-choice-swatch"
                          style={{ background: hex }}
                        />
                      ))}
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          <p className="theme-picker-note">
            Saved in your browser only — does not affect other users.
          </p>
        </div>
      )}
    </div>
  );
}
