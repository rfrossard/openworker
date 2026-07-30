import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import {
  buildMarkdownSlideDesignerPrompt,
  MarkdownSlideDesigner,
  parseMarkdownDeck,
} from "./MarkdownSlideDesigner";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const artifacts = [{
  path: "reports/strategy.md",
  name: "strategy.md",
  kind: "markdown",
  size: 200,
  modified_at: 1,
}];

describe("MarkdownSlideDesigner", () => {
  it("turns Markdown headings and content into editable slide data", () => {
    const deck = parseMarkdownDeck(`# Climate plan

## Why now
Delay increases cost.

- Regulation is changing
- Customers expect action

## Decision
Choose the first investment.`);
    expect(deck.title).toBe("Climate plan");
    expect(deck.slides).toHaveLength(2);
    expect(deck.slides[0]).toMatchObject({
      title: "Why now",
      takeaway: "Delay increases cost.",
      bullets: ["Regulation is changing", "Customers expect action"],
      layout: "auto",
    });
  });

  it("preserves Markdown tables and suggests semantic layouts", () => {
    const deck = parseMarkdownDeck(`# Results
## Comparison
| Option | Cost |
| --- | --- |
| A | 10 |
| B | 20 |`);
    expect(deck.slides[0].bullets).toEqual(["Option | Cost", "A | 10", "B | 20"]);
  });

  it("locks the reviewed layouts and image requirements into the composer brief", () => {
    const deck = parseMarkdownDeck("# Plan\n## Opportunity\nA new market.");
    deck.slides[0].layout = "image-right";
    const prompt = buildMarkdownSlideDesignerPrompt("reports/plan.md", deck, "atlas");
    expect(prompt).toContain('"layout": "image-right"');
    expect(prompt).toContain('"image_required": true');
    expect(prompt).toContain("minimum_images=1");
    expect(prompt).toContain("Do not silently replace a selected layout");
    const photographicPrompt = buildMarkdownSlideDesignerPrompt("reports/plan.md", deck, "science-studio");
    expect(photographicPrompt).toContain("cover_image_path");
    expect(photographicPrompt).toContain('"photo-right" template treatment');
  });

  it("loads real Markdown and updates the simulated slide when a style is selected", async () => {
    vi.spyOn(api, "readArtifact").mockResolvedValue({
      ok: true,
      path: "reports/strategy.md",
      kind: "markdown",
      content: "# Strategy\n## The choice\nAct this quarter.\n- Move now\n- Measure results",
    });
    const onCreate = vi.fn();
    render(<MarkdownSlideDesigner sessionId="session-1" artifacts={artifacts} onCreate={onCreate} />);
    fireEvent.click(screen.getByRole("button", { name: /Slide Designer/i }));
    await waitFor(() => expect(screen.getAllByText("The choice").length).toBeGreaterThan(0));
    fireEvent.click(screen.getByRole("button", { name: /Two columns/i }));
    expect(screen.getByTestId("slide-preview").className).toContain("layout-two-column");
    fireEvent.change(screen.getByLabelText("Slide title"), { target: { value: "A better choice" } });
    expect(screen.getByTestId("slide-preview").textContent).toContain("A better choice");
    fireEvent.click(screen.getByRole("button", { name: "Review in composer" }));
    await waitFor(() => expect(onCreate).toHaveBeenCalledOnce());
    expect(onCreate.mock.calls[0][0]).toContain('"layout": "two-column"');
  });

  it("applies template tokens to the preview and offers twenty-eight slide styles", async () => {
    vi.spyOn(api, "readArtifact").mockResolvedValue({
      ok: true,
      path: "reports/strategy.md",
      kind: "markdown",
      content: "# Strategy\n## The choice\nAct this quarter.\n- Move now\n- Measure results",
    });
    render(<MarkdownSlideDesigner sessionId="session-1" artifacts={artifacts} onCreate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Slide Designer/i }));
    await waitFor(() => expect(screen.getByTestId("slide-preview")).toBeTruthy());
    const preview = screen.getByTestId("slide-preview");
    expect(preview.dataset.template).toBe("atlas");
    const atlasStyle = preview.getAttribute("style");
    fireEvent.change(screen.getByLabelText("Presentation template"), {
      target: { value: "neon-flow" },
    });
    expect(preview.dataset.template).toBe("neon-flow");
    expect(preview.dataset.transition).toBe("push");
    expect(preview.dataset.motif).toBe("chart");
    expect(preview.getAttribute("style")).not.toBe(atlasStyle);
    expect(screen.getByText(/Animated neon gradient/i)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Presentation template"), {
      target: { value: "environmental-fieldwork" },
    });
    expect(preview.dataset.composition).toBe("torn-photo");
    expect(screen.getByText(/torn-paper edge/i)).toBeTruthy();
    expect(screen.getByLabelText("Presentation template").querySelectorAll("option")).toHaveLength(47);
    expect(screen.getByLabelText("Presentation template").querySelectorAll("optgroup")).toHaveLength(5);
    expect(screen.getByLabelText("Slide styles").querySelectorAll("button")).toHaveLength(28);
    expect(screen.getByText("Core")).toBeTruthy();
    expect(screen.getByText("Visual")).toBeTruthy();
    expect(screen.getByText("Narrative")).toBeTruthy();
    expect(screen.getByText("Data")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Image background/i }));
    expect(preview.className).toContain("layout-image-background");
  });

  it("auto-designs semantic rows and previews an editable chart", async () => {
    vi.spyOn(api, "readArtifact").mockResolvedValue({
      ok: true,
      path: "reports/strategy.md",
      kind: "markdown",
      content: "# Strategy\n## Segment growth\n- Core | 72\n- New | 44\n- Partner | 28",
    });
    render(<MarkdownSlideDesigner sessionId="session-1" artifacts={artifacts} onCreate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Slide Designer/i }));
    await waitFor(() => expect(screen.getByTestId("slide-preview")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Auto-design deck" }));
    expect(screen.getByTestId("slide-preview").className).toContain("layout-bar-chart");
    expect(screen.getByText("Data (Label | Value, one per line)")).toBeTruthy();
  });
});
