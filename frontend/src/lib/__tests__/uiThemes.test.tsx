import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ThemePicker } from "../../components/ThemePicker";
import { normalizeHex } from "../ruleColors";
import { parseUiTheme, resolveUserPalette, UI_THEMES } from "../uiThemes";

describe("uiThemes", () => {
  it("provides popular themes with valid hex previews and palettes", () => {
    const ids = UI_THEMES.map((t) => t.id);
    expect(ids).toEqual([
      "bahonavi",
      "catppuccin",
      "dracula",
      "github",
      "nord",
      "tokyo-night",
      "gruvbox",
    ]);

    for (const theme of UI_THEMES) {
      for (const mode of ["dark", "light"] as const) {
        const preview = theme.preview[mode];
        expect(normalizeHex(preview.bg)).not.toBeNull();
        expect(normalizeHex(preview.card)).not.toBeNull();
        expect(normalizeHex(preview.text)).not.toBeNull();
        expect(normalizeHex(preview.accent)).not.toBeNull();
        preview.swatches.forEach((s) => expect(normalizeHex(s)).not.toBeNull());
        if (theme.dataPalette) {
          for (const hex of Object.values(theme.dataPalette[mode])) {
            expect(normalizeHex(hex)).not.toBeNull();
          }
        }
      }
    }
  });

  it("parses stored theme ids safely and resolves user palette overlays", () => {
    expect(parseUiTheme("catppuccin")).toBe("catppuccin");
    expect(parseUiTheme("unknown")).toBe("bahonavi");
    expect(parseUiTheme(null)).toBe("bahonavi");

    const server = { bug: "#111111", custom_key: "#222222" };
    expect(resolveUserPalette(server, "bahonavi", "dark")).toBe(server);

    const dracula = resolveUserPalette(server, "dracula", "dark");
    expect(dracula.bug).toBe("#ff5555");
    expect(dracula.custom_key).toBe("#222222");
  });
});

describe("ThemePicker", () => {
  it("lets any user switch Light/Dark mode and popular color themes without admin", () => {
    const onChangeMode = vi.fn();
    const onChangeColorTheme = vi.fn();
    render(
      <ThemePicker
        mode="dark"
        colorTheme="bahonavi"
        onChangeMode={onChangeMode}
        onChangeColorTheme={onChangeColorTheme}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Appearance: Bahonavi Pulse Dark/i }));
    expect(screen.getByRole("dialog", { name: /Appearance and color themes/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Light/i }));
    expect(onChangeMode).toHaveBeenCalledWith("light");

    fireEvent.click(screen.getByRole("button", { name: /Catppuccin/i }));
    expect(onChangeColorTheme).toHaveBeenCalledWith("catppuccin");

    fireEvent.click(screen.getByRole("button", { name: /Dracula/i }));
    expect(onChangeColorTheme).toHaveBeenCalledWith("dracula");

    fireEvent.click(screen.getByRole("button", { name: /GitHub/i }));
    expect(onChangeColorTheme).toHaveBeenCalledWith("github");
  });
});
