import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EditModeBar } from "../../components/settings/EditModeBar";
import { extractRegexInput, MatcherInput } from "../../components/settings/MatcherInput";
import { RulePopover } from "../../components/settings/RulePopover";
import { popoverForSection } from "../../components/settings/useRuleEditor";
import type { RuleSetItem } from "../types";

const sampleRuleSet: RuleSetItem = {
  name: "default",
  revision: "rev1",
  rule: {
    project_ids: [],
    team: "Core",
    classification: [],
    contexts: { rules: [], require_assignment: false },
    workflow: { stages: [] },
    validation: {
      required_labels: {},
      required_fields: {},
      stale_threshold_days: 14,
      max_cycle_time_days: 30,
    },
    colors: {},
  },
};

describe("extractRegexInput", () => {
  it("parses slash-delimited and regex:-prefixed inputs", () => {
    expect(extractRegexInput("/^sprint-\\d+$/")).toBe("^sprint-\\d+$");
    expect(extractRegexInput("regex:^qa::")).toBe("^qa::");
    expect(extractRegexInput("plain")).toBeNull();
    expect(extractRegexInput("//")).toBeNull();
    expect(extractRegexInput("regex:")).toBeNull();
  });
});

describe("popoverForSection", () => {
  it("maps priority and type sections to the mix popover with the matching subTab", () => {
    expect(popoverForSection("priority")).toEqual({ id: "mix", subTab: "priority" });
    expect(popoverForSection("type")).toEqual({ id: "mix", subTab: "type" });
    expect(popoverForSection("stages")).toEqual({ id: "stages" });
    expect(popoverForSection("quality")).toEqual({ id: "quality" });
  });
});

describe("MatcherInput inline regex", () => {
  it("offers and adds a regex pattern when typing /.../", () => {
    const onChange = vi.fn();
    render(
      <MatcherInput
        id="test-matcher"
        kind="label"
        value={[]}
        inventory={[{ name: "type::bug", count: 3, color: null, textColor: null }]}
        ariaLabel="Labels"
        onChange={onChange}
      />,
    );
    const input = screen.getByRole("combobox", { name: "Labels" });
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: "/^iter-\\d+$/" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith(["regex:^iter-\\d+$"]);
  });
});

describe("RulePopover", () => {
  it("closes on Escape key and close button click", () => {
    const onClose = vi.fn();
    render(
      <RulePopover id="stages" title="Workflow Stages" anchor={null} onClose={onClose}>
        <div>Editor body</div>
      </RulePopover>,
    );
    expect(screen.getByRole("dialog", { name: "Workflow Stages" })).toBeInTheDocument();
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Close Workflow Stages" }));
    expect(onClose).toHaveBeenCalledTimes(2);
  });
});

describe("EditModeBar", () => {
  it("shows chart shortcuts when charts are hidden and opens More menu items", () => {
    const onOpenPopover = vi.fn();
    const onSave = vi.fn();
    render(
      <EditModeBar
        loadState="ready"
        loadError={null}
        chartsVisible={false}
        ruleSets={[sampleRuleSet]}
        selected={sampleRuleSet}
        defaultName="default"
        dirty
        saving={false}
        problemCount={0}
        problemCountBySection={{ impact: 1 }}
        unplacedProblems={[]}
        loadErrorNotice={null}
        notice={null}
        activePopover={null}
        onRetryLoad={vi.fn()}
        onSelectRuleSet={vi.fn()}
        onOpenPopover={onOpenPopover}
        onNewRuleSet={vi.fn()}
        onDiscard={vi.fn()}
        onSave={onSave}
        onDismissNotice={vi.fn()}
        onReloadLatest={vi.fn()}
        onLock={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: /Types & Priority/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Stages/i })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Impact/i }));
    expect(onOpenPopover).toHaveBeenCalledWith("impact", expect.any(HTMLElement), "bottom", undefined);

    fireEvent.click(screen.getByRole("button", { name: /More/i }));
    fireEvent.click(screen.getByRole("menuitem", { name: /View YAML/i }));
    expect(onOpenPopover).toHaveBeenCalledWith("text", expect.any(HTMLElement), "bottom");

    fireEvent.click(screen.getByRole("button", { name: /Save & apply/i }));
    expect(onSave).toHaveBeenCalledTimes(1);
  });
});
