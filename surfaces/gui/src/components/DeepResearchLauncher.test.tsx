import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { buildDeepResearchPrompt, DeepResearchLauncher } from "./DeepResearchLauncher";

describe("Deep Research launcher", () => {
  it("builds a persistent, cited research artifact task", () => {
    const prompt = buildDeepResearchPrompt({
      question: "Should we enter the Japanese market?",
      depth: "deep",
      plan: "Size the market\nCompare competitors",
    });

    expect(prompt).toContain("Should we enter the Japanese market?");
    expect(prompt).toContain("at least 20 credible sources");
    expect(prompt).toContain("1. Size the market");
    expect(prompt).toContain("persistent Markdown artifact");
    expect(prompt).toContain("Cite sources inline");
  });

  it("lets the user review the generated task in the composer", () => {
    const onCreate = vi.fn();
    render(<DeepResearchLauncher onCreate={onCreate} />);

    fireEvent.click(screen.getByRole("button", { name: "New research" }));
    fireEvent.change(screen.getByLabelText("Research question"), {
      target: { value: "Compare secure browser frameworks" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Deep/ }));
    fireEvent.click(screen.getByRole("button", { name: "Review in composer" }));

    expect(onCreate).toHaveBeenCalledTimes(1);
    expect(onCreate.mock.calls[0][0]).toContain("Compare secure browser frameworks");
    expect(onCreate.mock.calls[0][0]).toContain("at least 20 credible sources");
  });
});
