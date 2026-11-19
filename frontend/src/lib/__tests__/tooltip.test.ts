import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { createElement } from "react";
import { ChartTooltip, placeTooltip } from "../../components/charts/ChartTooltip";

const viewport = { width: 1000, height: 800 };
const size = { width: 200, height: 100 };

function contains(
  pos: { left: number; top: number },
  cursor: { x: number; y: number },
): boolean {
  return (
    cursor.x >= pos.left &&
    cursor.x <= pos.left + size.width &&
    cursor.y >= pos.top &&
    cursor.y <= pos.top + size.height
  );
}

describe("placeTooltip", () => {
  it("places the box right of and below the cursor by default", () => {
    expect(placeTooltip({ x: 100, y: 100 }, size, viewport)).toEqual({ left: 114, top: 114 });
  });

  it("flips left near the right edge and keeps the cursor outside", () => {
    const cursor = { x: 900, y: 100 };
    const pos = placeTooltip(cursor, size, viewport);
    expect(pos).toEqual({ left: 686, top: 114 });
    expect(contains(pos, cursor)).toBe(false);
  });

  it("flips up near the bottom edge and keeps the cursor outside", () => {
    const cursor = { x: 100, y: 750 };
    const pos = placeTooltip(cursor, size, viewport);
    expect(pos).toEqual({ left: 114, top: 636 });
    expect(contains(pos, cursor)).toBe(false);
  });

  it("flips both ways in the bottom-right corner", () => {
    const cursor = { x: 990, y: 790 };
    const pos = placeTooltip(cursor, size, viewport);
    expect(pos).toEqual({ left: 776, top: 676 });
    expect(contains(pos, cursor)).toBe(false);
  });

  it("clamps into the viewport when neither side fits", () => {
    const pos = placeTooltip({ x: 100, y: 100 }, { width: 300, height: 100 }, { width: 350, height: 800 });
    expect(pos.left).toBe(8);
  });
});

describe("ChartTooltip", () => {
  it("renders into document.body so a scrolling chart container cannot clip it", () => {
    const { container } = render(
      createElement(
        "div",
        { style: { overflowY: "auto" } },
        createElement(ChartTooltip, { tooltip: { x: 10, y: 10, content: "Tech Debt" } }),
      ),
    );
    const tip = document.querySelector(".chart-tooltip");
    expect(tip).not.toBeNull();
    expect(container.contains(tip)).toBe(false);
    expect(tip?.parentElement).toBe(document.body);
  });
});
