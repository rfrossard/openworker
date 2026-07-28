import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { buildManusPresentationPrompt, ManusPresentationLauncher } from "./ManusPresentationLauncher";

afterEach(cleanup);

describe("ManusPresentationLauncher", () => {
  it("builds a render-and-revise harness prompt", () => {
    const prompt = buildManusPresentationPrompt({
      topic: "The future of local AI",
      audience: "Executive team",
      outcome: "Choose an investment",
      slideCount: 12,
      depth: "deep",
      visualDirection: "Editorial",
      generateImages: true,
    });
    expect(prompt).toContain("Manus-style Presentation harness");
    expect(prompt).toContain("RESEARCHER");
    expect(prompt).toContain("PRESENTER");
    expect(prompt).toContain("ENVIRONMENT-GROUNDED REFLECTION");
    expect(prompt).toContain("Nano Banana 2 Lite");
    expect(prompt).toContain("build_presentation");
    expect(prompt).toContain(".presentation.json");
    expect(prompt).toContain("rendered slide previews");
    expect(prompt).toContain('template_id="atlas"');
  });

  it("sends a complete English brief to the composer", () => {
    const onCreate = vi.fn();
    render(<ManusPresentationLauncher artifacts={[]} onCreate={onCreate} />);
    fireEvent.click(screen.getByRole("button", { name: /Manus-style presentation/i }));
    fireEvent.change(screen.getByLabelText("Topic or brief"), {
      target: { value: "A clear climate strategy" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Review in composer" }));
    expect(onCreate).toHaveBeenCalledOnce();
    expect(onCreate.mock.calls[0][0]).toContain("A clear climate strategy");
    expect(onCreate.mock.calls[0][0]).toContain("Target length: 10 slides");
  });

  it("offers at least ten editable built-in templates", () => {
    render(<ManusPresentationLauncher artifacts={[]} onCreate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Manus-style presentation/i }));
    const options = screen.getByLabelText("Editable PowerPoint template").querySelectorAll("option");
    expect(options.length).toBeGreaterThanOrEqual(10);
  });
});
