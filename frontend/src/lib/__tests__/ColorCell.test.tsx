import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { ColorCell } from "../../components/settings/ColorCell";
import { setColor, type ColorMap } from "../ruleColors";
import type { PaletteDefaults } from "../types";

const defaults: PaletteDefaults = { light: { bug: "#111111" }, dark: { bug: "#222222" } };

function Harness({ onSet, initial = {} }: { onSet: (hex: string) => void; initial?: ColorMap }) {
  const [colors, setColors] = useState<ColorMap>(initial);
  return (
    <ColorCell
      idBase="t"
      theme="light"
      name="Bug"
      colorKey="bug"
      hasDefault
      colors={colors}
      defaults={defaults}
      onSet={(hex) => {
        onSet(hex);
        setColors(setColor(colors, "light", "bug", hex));
      }}
      onReset={() => undefined}
    />
  );
}

function type(input: HTMLElement, value: string) {
  fireEvent.focus(input);
  fireEvent.change(input, { target: { value: "" } });
  for (let i = 1; i <= value.length; i += 1) {
    fireEvent.change(input, { target: { value: value.slice(0, i) } });
  }
}

describe("ColorCell hex field", () => {
  it("accepts a 6-digit colour typed character by character", () => {
    const onSet = vi.fn();
    render(<Harness onSet={onSet} />);
    const input = screen.getByLabelText("Bug colour code for the light theme");
    type(input, "#1a7a62");
    expect(onSet).toHaveBeenCalledTimes(1);
    expect(onSet).toHaveBeenCalledWith("#1a7a62");
    expect(input).toHaveValue("#1a7a62");
  });

  it("commits a 3-digit colour on blur", () => {
    const onSet = vi.fn();
    render(<Harness onSet={onSet} />);
    const input = screen.getByLabelText("Bug colour code for the light theme");
    type(input, "#abc");
    expect(onSet).not.toHaveBeenCalled();
    fireEvent.blur(input);
    expect(onSet).toHaveBeenCalledWith("#aabbcc");
    expect(input).toHaveValue("#aabbcc");
  });

  it("does not write an override when focus passes through unchanged", () => {
    const onSet = vi.fn();
    render(<Harness onSet={onSet} />);
    const input = screen.getByLabelText("Bug colour code for the light theme");
    fireEvent.focus(input);
    fireEvent.blur(input);
    fireEvent.focus(input);
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSet).not.toHaveBeenCalled();
  });

  it("does not write when the same code is retyped", () => {
    const onSet = vi.fn();
    render(<Harness onSet={onSet} initial={{ light: { bug: "#1a7a62" } }} />);
    const input = screen.getByLabelText("Bug colour code for the light theme");
    type(input, "#1A7A62");
    fireEvent.blur(input);
    expect(onSet).not.toHaveBeenCalled();
  });
});
