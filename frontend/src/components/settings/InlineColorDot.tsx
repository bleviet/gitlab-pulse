import { RotateCcw } from "lucide-react";
import {
  canReset,
  effectiveColor,
  normalizeHex,
  type ColorMap,
  type ColorTheme,
} from "../../lib/ruleColors";
import type { PaletteDefaults } from "../../lib/types";

interface InlineColorDotProps {
  name: string;
  colorKey: string;
  colors: ColorMap;
  defaults: PaletteDefaults;
  theme: ColorTheme;
  canEdit: boolean;
  onSet: (hex: string) => void;
  onReset: () => void;
}

export function InlineColorDot({
  name,
  colorKey,
  colors,
  defaults,
  theme,
  canEdit,
  onSet,
  onReset,
}: InlineColorDotProps) {
  const key = colorKey.trim().toLowerCase();
  const current = key ? effectiveColor(colors, defaults, theme, key) : null;
  const resettable = canEdit && key !== "" && canReset(colors, defaults, theme, key);
  const labelName = name.trim() || "row";

  if (!canEdit || key === "") {
    return (
      <span
        className="rule-color-dot readonly"
        style={current ? { background: current } : undefined}
        title={
          key === ""
            ? "Name this item first to pick a colour"
            : "Colours are shared across teams (edit in the default rule set)"
        }
        aria-hidden="true"
      />
    );
  }

  return (
    <span className="rule-color-wrap">
      <label
        className="rule-color-dot"
        style={current ? { background: current } : undefined}
        title={`Change ${labelName} colour (${theme} theme)`}
      >
        <input
          type="color"
          className="rule-color-native"
          aria-label={`${labelName} colour (${theme} theme)`}
          value={normalizeHex(current ?? "") ?? "#4facfe"}
          onChange={(e) => onSet(e.target.value)}
        />
      </label>
      {resettable && (
        <button
          type="button"
          className="rule-color-reset"
          aria-label={`Reset ${labelName} colour`}
          title="Reset to default colour"
          onClick={onReset}
        >
          <RotateCcw size={10} />
        </button>
      )}
    </span>
  );
}
