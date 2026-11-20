import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "../api";
import type { ImpactSummary, RulePreviewResponse, RuleSetBody } from "../types";

const previewRuleSet = vi.fn();
vi.mock("../api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api")>()),
  previewRuleSet: (...args: unknown[]) => previewRuleSet(...args),
}));

import { PREVIEW_DEBOUNCE_MS, useRulePreview } from "../../components/settings/useRulePreview";

function rule(team: string): RuleSetBody {
  return { team } as RuleSetBody;
}

function response(total: number): RulePreviewResponse {
  return { problems: [], impact: { total_issues: total } as ImpactSummary };
}

describe("useRulePreview", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    previewRuleSet.mockReset();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("makes no request when disabled", async () => {
    renderHook(() => useRulePreview({ enabled: false, name: "a", draft: rule("x") }));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(2000);
    });
    expect(previewRuleSet).not.toHaveBeenCalled();
  });

  it("requests on mount, then debounces quick edits into one request", async () => {
    previewRuleSet.mockResolvedValue(response(1));
    const { result, rerender } = renderHook(
      ({ draft }) => useRulePreview({ enabled: true, name: "a", draft }),
      { initialProps: { draft: rule("1") } },
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(previewRuleSet).toHaveBeenCalledTimes(1);
    expect(result.current.status).toBe("ready");

    rerender({ draft: rule("2") });
    rerender({ draft: rule("3") });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS - 1);
    });
    expect(previewRuleSet).toHaveBeenCalledTimes(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1);
    });
    expect(previewRuleSet).toHaveBeenCalledTimes(2);
    expect(previewRuleSet.mock.calls[1][1]).toEqual(rule("3"));
  });

  it("ignores a stale response and keeps the previous impact while loading", async () => {
    let resolveSecond: (r: RulePreviewResponse) => void = () => undefined;
    previewRuleSet
      .mockResolvedValueOnce(response(1))
      .mockReturnValueOnce(new Promise<RulePreviewResponse>((r) => (resolveSecond = r)))
      .mockResolvedValueOnce(response(3));
    const { result, rerender } = renderHook(
      ({ draft }) => useRulePreview({ enabled: true, name: "a", draft }),
      { initialProps: { draft: rule("1") } },
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    rerender({ draft: rule("2") });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    });
    expect(result.current.status).toBe("loading");
    expect(result.current.impact?.total_issues).toBe(1);

    rerender({ draft: rule("3") });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    });
    expect(result.current.impact?.total_issues).toBe(3);

    await act(async () => {
      resolveSecond(response(2));
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.impact?.total_issues).toBe(3);
  });

  it("clears problems and exposes the error when a request fails", async () => {
    previewRuleSet
      .mockResolvedValueOnce({
        problems: [{ path: "x", message: "bad" }],
        impact: null,
      })
      .mockRejectedValueOnce(new ApiError("Server said no", 409));
    const { result, rerender } = renderHook(
      ({ draft }) => useRulePreview({ enabled: true, name: "a", draft }),
      { initialProps: { draft: rule("1") } },
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.problems).toHaveLength(1);

    rerender({ draft: rule("2") });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    });
    expect(result.current.status).toBe("error");
    expect(result.current.error).toBe("Server said no");
    expect(result.current.problems).toEqual([]);
    expect(result.current.unauthorized).toBe(false);
  });

  it("flags a 401", async () => {
    previewRuleSet.mockRejectedValue(new ApiError("Not logged in", 401));
    const stable = rule("1");
    const { result } = renderHook(() =>
      useRulePreview({ enabled: true, name: "a", draft: stable }),
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.status).toBe("error");
    expect(result.current.unauthorized).toBe(true);
  });

  it("does not report an aborted request as an error", async () => {
    let rejectFirst: (e: Error) => void = () => undefined;
    previewRuleSet
      .mockReturnValueOnce(new Promise<RulePreviewResponse>((_, rej) => (rejectFirst = rej)))
      .mockResolvedValueOnce(response(2));
    const { result, rerender } = renderHook(
      ({ draft }) => useRulePreview({ enabled: true, name: "a", draft }),
      { initialProps: { draft: rule("1") } },
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    rerender({ draft: rule("2") });
    await act(async () => {
      rejectFirst(new DOMException("aborted", "AbortError"));
      await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    });
    expect(result.current.status).toBe("ready");
    expect(result.current.error).toBeNull();
  });

  it("drops the previous result when the rule set changes", async () => {
    previewRuleSet
      .mockResolvedValueOnce({
        problems: [{ path: "x", message: "bad" }],
        impact: { total_issues: 1 } as ImpactSummary,
      })
      .mockReturnValueOnce(new Promise<RulePreviewResponse>(() => undefined));
    const stable = rule("1");
    const { result, rerender } = renderHook(
      ({ name }) => useRulePreview({ enabled: true, name, draft: stable }),
      { initialProps: { name: "a" } },
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.impact).not.toBeNull();

    rerender({ name: "b" });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.status).toBe("loading");
    expect(result.current.impact).toBeNull();
    expect(result.current.problems).toEqual([]);
  });

  it("marks the result pending while the draft differs from the calculated one", async () => {
    previewRuleSet.mockResolvedValue(response(1));
    const { result, rerender } = renderHook(
      ({ draft }) => useRulePreview({ enabled: true, name: "a", draft }),
      { initialProps: { draft: rule("1") } },
    );
    await act(async () => {
      await vi.advanceTimersByTimeAsync(0);
    });
    expect(result.current.pending).toBe(false);
    rerender({ draft: rule("2") });
    expect(result.current.pending).toBe(true);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(PREVIEW_DEBOUNCE_MS);
    });
    expect(result.current.pending).toBe(false);
  });
});
