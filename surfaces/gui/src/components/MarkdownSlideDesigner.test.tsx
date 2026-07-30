import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import {
  applyContentElement,
  buildMarkdownSlideDesignerPrompt,
  MarkdownSlideDesigner,
  parseMarkdownDeck,
  presentationImageEstimate,
  presentationPreflight,
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

  it("applies a structured element without replacing the user's content", () => {
    const deck = parseMarkdownDeck("# Plan\n## Sequence\nKeep this message.\n- Discover\n- Decide");
    deck.slides[0].imageRequired = true;
    const result = applyContentElement(deck.slides[0], "timeline");
    expect(result).toMatchObject({
      layout: "timeline",
      takeaway: "Keep this message.",
      bullets: ["Discover", "Decide"],
      imageRequired: false,
    });
  });

  it("locks the reviewed layouts and image requirements into the composer brief", () => {
    const deck = parseMarkdownDeck("# Plan\n## Opportunity\nA new market.");
    deck.slides[0].layout = "image-right";
    deck.slides[0].imageRequired = true;
    deck.slides[0].imagePrompt = "Editorial market scene with negative space on the left";
    const prompt = buildMarkdownSlideDesignerPrompt("reports/plan.md", deck, "atlas");
    expect(prompt).toContain('"layout": "image-right"');
    expect(prompt).toContain('"image_required": true');
    expect(prompt).toContain("minimum_images=1");
    expect(prompt).toContain("estimated at USD 0.0336");
    expect(prompt).toContain('"image_prompt": "Editorial market scene');
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
    fireEvent.change(screen.getByLabelText("Slide title"), { target: { value: "A better choice" } });
    expect(screen.getByTestId("slide-preview").textContent).toContain("A better choice");
    fireEvent.click(screen.getByRole("button", { name: "Continue to design" }));
    fireEvent.click(screen.getByRole("button", { name: /Two columns/i }));
    expect(screen.getByTestId("slide-preview").className).toContain("layout-two-column");
    fireEvent.click(screen.getByRole("button", { name: "Review deck" }));
    fireEvent.click(screen.getByRole("button", { name: "Create in composer" }));
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
    fireEvent.click(screen.getByRole("button", { name: "Continue to design" }));
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
    fireEvent.click(screen.getByRole("button", { name: "Continue to design" }));
  });

  it("offers structured elements in the content step and updates guidance immediately", async () => {
    vi.spyOn(api, "readArtifact").mockResolvedValue({
      ok: true,
      path: "reports/strategy.md",
      kind: "markdown",
      content: "# Strategy\n## Growth\nKeep the source content.\n- Enterprise | 64\n- Consumer | 36",
    });
    render(<MarkdownSlideDesigner sessionId="session-1" artifacts={artifacts} onCreate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Slide Designer/i }));
    await waitFor(() => expect(screen.getByTestId("slide-preview")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Bar chart Compare values" }));
    expect(screen.getByTestId("slide-preview").className).toContain("layout-bar-chart");
    expect(screen.getByText("Data (Label | Value, one per line)")).toBeTruthy();
    expect(screen.getByText("Example: Enterprise | 64")).toBeTruthy();
    expect((screen.getByLabelText("Supporting points") as HTMLTextAreaElement).value).toBe("Enterprise | 64\nConsumer | 36");
  });

  it("shows a transparent image budget and keeps paid generation approval-gated", async () => {
    vi.spyOn(api, "readArtifact").mockResolvedValue({
      ok: true,
      path: "reports/strategy.md",
      kind: "markdown",
      content: "# Strategy\n## The choice\nAct this quarter.",
    });
    render(<MarkdownSlideDesigner sessionId="session-1" artifacts={artifacts} onCreate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Slide Designer/i }));
    await waitFor(() => expect(screen.getByTestId("slide-preview")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Continue to design" }));
    fireEvent.click(screen.getByLabelText("Generate an original visual"));
    fireEvent.change(screen.getByLabelText("Visual direction"), { target: { value: "A calm editorial scene" } });
    fireEvent.click(screen.getByRole("button", { name: "Review deck" }));
    expect(screen.getByText("USD 0.0336")).toBeTruthy();
    expect(screen.getByText(/No paid image call happens in this screen/i)).toBeTruthy();
  });

  it("calculates the image ceiling from approved visual slides only", () => {
    const deck = parseMarkdownDeck("# Deck\n## One\nFirst\n## Two\nSecond");
    deck.slides[1].imageRequired = true;
    expect(presentationImageEstimate(deck)).toEqual({ images: 1, estimatedCostUsd: 0.0336 });
  });

  it("blocks creation when a paid visual has no approved direction", () => {
    const deck = parseMarkdownDeck("# Deck\n## Visual proof\nOne message");
    deck.slides[0].imageRequired = true;
    expect(presentationPreflight(deck)).toMatchObject({
      passed: false,
      issues: ["Slide 1 needs visual direction before image generation."],
    });
    deck.slides[0].imagePrompt = "A documentary-style close-up with negative space";
    expect(presentationPreflight(deck).passed).toBe(true);
  });

  it("keeps footer actions outside and after the scrollable style workspace", async () => {
    vi.spyOn(api, "readArtifact").mockResolvedValue({
      ok: true,
      path: "reports/strategy.md",
      kind: "markdown",
      content: "# Strategy\n## One clear choice\nAct this quarter.",
    });
    render(<MarkdownSlideDesigner sessionId="session-1" artifacts={artifacts} onCreate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Slide Designer/i }));
    await waitFor(() => expect(screen.getByTestId("slide-preview")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Continue to design" }));
    const styles = screen.getByLabelText("Slide styles");
    const footer = screen.getByRole("button", { name: "Review deck" }).closest("footer");
    expect(footer).toBeTruthy();
    expect(styles.closest(".slide-designer-workspace")).toBeTruthy();
    expect(footer?.contains(styles)).toBe(false);
    expect(styles.compareDocumentPosition(footer as Node) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
