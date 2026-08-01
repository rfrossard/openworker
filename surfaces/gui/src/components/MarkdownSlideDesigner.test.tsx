import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "../api";
import {
  applyContentElement,
  applyResearchVisualPlan,
  autoFixPresentation,
  buildMarkdownSlideDesignerPrompt,
  MarkdownSlideDesigner,
  parseMarkdownDeck,
  presentationImageEstimate,
  presentationPreflight,
  presentationQualityReport,
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

  it("separates audience copy from slide-production directives", () => {
    const deck = parseMarkdownDeck(`# Agent protocols

## Slide 1: The protocol stack
- **Narrative job:** Establish why the stack matters.
- **Takeaway:** MCP connects tools while A2A connects agents.
- **Transition:** Fade
- **Layout:** image-right
- **Image:** reports/assets/protocol-stack.png (generated)
- **Sources:**
MCP specification: https://modelcontextprotocol.io/specification
A2A Protocol: https://a2a-protocol.org/latest/

- Each protocol solves a different interoperability layer.`);

    expect(deck.slides[0]).toMatchObject({
      title: "The protocol stack",
      takeaway: "MCP connects tools while A2A connects agents.",
      bullets: ["Each protocol solves a different interoperability layer."],
      layout: "image-right",
      imageRequired: true,
      imagePrompt: "reports/assets/protocol-stack.png (generated)",
      sourceUrls: [
        "https://modelcontextprotocol.io/specification",
        "https://a2a-protocol.org/latest/",
      ],
      visualPlanReason: "Establish why the stack matters.",
      visualPlanData: { transition: "Fade" },
    });
    expect(JSON.stringify(deck.slides[0])).not.toContain("Slide 1:");
    expect([deck.slides[0].takeaway, ...deck.slides[0].bullets].join(" ")).not.toMatch(
      /Narrative job|Transition:|Layout:|Sources:|MCP specification:/,
    );
  });

  it("removes compact S-number production prefixes from audience-facing titles", () => {
    const deck = parseMarkdownDeck(`# Brief
## S1 - The decision
Choose the secure option.
## S2: Evidence first
Compare the sources.`);
    expect(deck.slides.map((slide) => slide.title)).toEqual(["The decision", "Evidence first"]);
  });

  it("treats the storyboard preamble as a deck brief rather than a slide", () => {
    const deck = parseMarkdownDeck(`# Storyboard: Agent protocols

**Audience:** Technology leaders
**Outcome:** Choose an interoperability architecture
**Takeaway:** MCP and A2A are complementary.

---

## Slide 1: Title Slide
- **Narrative job:** Establish the frame.
- **Takeaway:** The protocol stack is becoming infrastructure.

## Slide 2: The decision
- **Takeaway:** Use each protocol for its intended layer.`);

    expect(deck.title).toBe("Agent protocols");
    expect(deck.slides).toHaveLength(2);
    expect(deck.slides.map((slide) => slide.title)).toEqual(["Title Slide", "The decision"]);
    expect(JSON.stringify(deck.slides)).not.toMatch(/Audience:|Outcome:|Technology leaders/);
  });

  it("does not offer source ledgers as presentation Markdown", async () => {
    const presentationArtifacts = [
      {
        path: "reports/protocol.sources.md",
        name: "protocol.sources.md",
        kind: "markdown",
        size: 100,
        modified_at: 1,
      },
      {
        path: "reports/protocol-storyboard.md",
        name: "protocol-storyboard.md",
        kind: "markdown",
        size: 100,
        modified_at: 2,
      },
    ];
    vi.spyOn(api, "readArtifact").mockResolvedValue({
      ok: true,
      path: "reports/protocol-storyboard.md",
      kind: "markdown",
      content: "# Protocols\n## Slide 1: The choice\nChoose deliberately.",
    });
    render(<MarkdownSlideDesigner sessionId="session-1" artifacts={presentationArtifacts} onCreate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Slide Designer/i }));
    await waitFor(() => expect(screen.getByTestId("slide-preview")).toBeTruthy());
    const selector = screen.getByLabelText("Deep Research Result") as HTMLSelectElement;
    expect(selector.value).toBe("reports/protocol-storyboard.md");
    expect(selector.querySelectorAll("option")).toHaveLength(1);
    expect(screen.queryByText("protocol.sources.md")).toBeNull();
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

  it("reads Deep Research visual data from Markdown without rendering production instructions", () => {
    const deck = parseMarkdownDeck(`# Results
## Slide 2: Options at a glance
- **Narrative job:** Compare the verified alternatives.
- **Takeaway:** Option A costs less.
\`\`\`openworker-visual
{
  "type": "table",
  "reason": "The alternatives share comparable fields.",
  "visual_question": "Which option costs less?",
  "data_shape": "comparison",
  "selection_confidence": 0.94,
  "rejected_representations": [{"type": "bar_chart", "reason": "It would hide the option names."}],
  "design_spec": {"emphasis": "A", "sort": "ascending"},
  "data": {
    "columns": ["Option", "Cost"],
    "rows": [["A", "$10"], ["B", "$20"]]
  },
  "claim_ids": ["C1", "C2"],
  "sources": ["https://example.com/data"]
}
\`\`\``);
    expect(deck.slides[0]).toMatchObject({
      title: "Options at a glance",
      takeaway: "Option A costs less.",
      layout: "table",
      bullets: ["Option | Cost", "A | $10", "B | $20"],
      claimIds: ["C1", "C2"],
      sourceUrls: ["https://example.com/data"],
      visualPlanReason: "The alternatives share comparable fields.",
    });
    expect(deck.slides[0].visualPlanData).toMatchObject({
      visual_question: "Which option costs less?",
      data_shape: "comparison",
      selection_confidence: 0.94,
      design_spec: { emphasis: "A", sort: "ascending" },
    });
    expect(JSON.stringify(deck)).not.toContain("openworker-visual");
    expect(JSON.stringify(deck)).not.toContain("Narrative job:");
  });

  it("honors a Deep Research layout recommendation while keeping it user-editable", () => {
    const deck = parseMarkdownDeck(`# Results
## Slide 1: Adoption
The first milestone is complete.
\`\`\`openworker-visual
{"type":"metrics","layout_recommendation":"big_number","data":{"value":"64%","label":"adoption"}}
\`\`\``);
    expect(deck.slides[0]).toMatchObject({
      title: "Adoption",
      layout: "big-number",
      recommendedLayout: "big-number",
    });
    expect(applyContentElement(deck.slides[0], "table")).toMatchObject({
      layout: "table",
      recommendedLayout: "big-number",
    });
  });

  it("flags decorative or overly dense visual choices and auto-fixes safe cases", () => {
    const deck = parseMarkdownDeck(`# Quality
## Composition
\`\`\`openworker-visual
{"type":"donut_chart","data":{"series":[{"label":"A","value":30},{"label":"B","value":25},{"label":"C","value":20},{"label":"D","value":10},{"label":"E","value":8},{"label":"F","value":7}]}}
\`\`\`
## Decision path
\`\`\`openworker-visual
{"type":"flowchart","visual_question":"What happens next?","data_shape":"sequence","data":{"items":[{"label":"Research"},{"label":"Build"},{"label":"Launch"}]}}
\`\`\``);
    const report = presentationQualityReport(deck);
    expect(report.findings.map((finding) => finding.id)).toContain("donut-density-0");
    expect(report.findings.map((finding) => finding.id)).toContain("flow-sequence-1");
    const fixed = autoFixPresentation(deck);
    expect(fixed.deck.slides[0].layout).toBe("bar-chart");
    expect(fixed.deck.slides[1].layout).toBe("process");
  });

  it("maps grounded research sections into editable semantic slide representations", () => {
    const deck = parseMarkdownDeck(`# Evidence deck
## Market evidence
Original prose.
## Verified voice
Original quote.
## Decision flow
Original flow.
## Team
Original hierarchy.
## Milestones
Original timeline.
## Delivery
Original process.
## Field evidence
Original visual.`);
    const applied = applyResearchVisualPlan(deck, JSON.stringify({
      schema_version: "openworker.deep-research.v2",
      sections: [
        {
          title: "Slide 1: Market evidence",
          takeaway: "Takeaway: Segment A leads the market.",
          claim_ids: ["C1", "C2"],
          sources: ["https://example.com/data"],
          representation: {
            type: "bar_chart",
            reason: "The categories share one comparable measure.",
            data: {
              series: [
                { label: "Segment A", value: 64, claim_ids: ["C1"] },
                { label: "Segment B", value: 36, claim_ids: ["C2"] },
              ],
            },
          },
        },
        {
          title: "Verified voice",
          representation: {
            type: "quote",
            data: { quote: { text: "Evidence changes the decision.", attribution: "Primary interview" } },
          },
        },
        {
          title: "Decision flow",
          representation: {
            type: "flowchart",
            data: { items: [{ label: "Screen" }, { label: "Verify" }, { label: "Decide" }] },
          },
        },
        {
          title: "Team",
          representation: {
            type: "org_chart",
            data: { relationships: [{ parent: "Lead", child: "Research" }, { parent: "Lead", child: "Design" }] },
          },
        },
        {
          title: "Milestones",
          representation: {
            type: "timeline",
            data: { items: [{ date: "Q1", label: "Pilot" }, { date: "Q2", label: "Launch" }] },
          },
        },
        {
          title: "Delivery",
          representation: {
            type: "process",
            data: { steps: [{ label: "Discover" }, { label: "Build" }, { label: "Validate" }] },
          },
        },
        {
          title: "Field evidence",
          claim_ids: ["C7"],
          representation: { type: "image", reason: "A field photograph makes the context concrete.", data: {} },
          visual_references: [{
            url: "https://example.com/reference.jpg",
            description: "Wide field scene with the subject on the right",
            purpose: "Illustrate operating context",
            source_type: "licensed",
            license: "Reference only",
            claim_ids: ["C7"],
          }],
        },
      ],
    }));

    expect(applied).toMatchObject({ appliedSections: 7, warning: "" });
    expect(applied.deck.slides[0]).toMatchObject({
      title: "Market evidence",
      layout: "bar-chart",
      takeaway: "Segment A leads the market.",
      bullets: ["Segment A | 64", "Segment B | 36"],
      claimIds: ["C1", "C2"],
      sourceUrls: ["https://example.com/data"],
      visualPlanReason: "The categories share one comparable measure.",
      visualPlanData: {
        series: [
          { label: "Segment A", value: 64, claim_ids: ["C1"] },
          { label: "Segment B", value: 36, claim_ids: ["C2"] },
        ],
      },
    });
    expect(applied.deck.slides[1]).toMatchObject({
      layout: "quote",
      takeaway: "Evidence changes the decision.",
      bullets: ["Primary interview"],
    });
    expect(applied.deck.slides[2]).toMatchObject({ layout: "flow-diagram", bullets: ["Screen", "Verify", "Decide"] });
    expect(applied.deck.slides[3]).toMatchObject({ layout: "org-chart", bullets: ["Lead > Research", "Lead > Design"] });
    expect(applied.deck.slides[4]).toMatchObject({ layout: "timeline", bullets: ["Q1 — Pilot", "Q2 — Launch"] });
    expect(applied.deck.slides[5]).toMatchObject({ layout: "process", bullets: ["Discover", "Build", "Validate"] });
    expect(applied.deck.slides[6]).toMatchObject({
      layout: "image-right",
      imageRequired: true,
      claimIds: ["C7"],
      imagePrompt: expect.stringContaining("Wide field scene"),
      visualReferences: [expect.objectContaining({ sourceType: "licensed", license: "Reference only" })],
    });
  });

  it("preserves Markdown when the companion visual ledger is malformed", () => {
    const deck = parseMarkdownDeck("# Plan\n## Decision\nKeep the verified prose.");
    const applied = applyResearchVisualPlan(deck, "{not-json");
    expect(applied.appliedSections).toBe(0);
    expect(applied.warning).toContain("invalid");
    expect(applied.deck).toEqual(deck);
  });

  it("edits a Markdown table as cells while preserving pipe-separated rows", async () => {
    vi.spyOn(api, "readArtifact").mockResolvedValue({
      ok: true,
      path: "reports/strategy.md",
      kind: "markdown",
      content: "# Results\n## Comparison\n| Option | Cost |\n| --- | --- |\n| A | 10 |\n| B | 20 |",
    });
    render(<MarkdownSlideDesigner sessionId="session-1" artifacts={artifacts} onCreate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Slide Designer/i }));
    await waitFor(() => expect(screen.getByTestId("slide-preview")).toBeTruthy());
    const researchResult = screen.getByLabelText("Deep Research Result") as HTMLSelectElement;
    expect(researchResult.options[researchResult.selectedIndex]?.text).toBe("strategy.md (Research)");
    expect(screen.getByText("Deep Research Result: Results")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Continue to design" }));
    fireEvent.click(screen.getByRole("button", { name: "Table Rows and columns" }));
    expect((screen.getByLabelText("Row 1 column 1") as HTMLInputElement).value).toBe("Option");
    fireEvent.change(screen.getByLabelText("Row 2 column 2"), { target: { value: "12" } });
    expect(screen.getByTestId("slide-preview").textContent).toContain("12");
    fireEvent.click(screen.getByRole("button", { name: "+ Column" }));
    expect(screen.getByLabelText("Row 1 column 3")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Delete column" }));
    expect(screen.queryByLabelText("Row 1 column 3")).toBeNull();
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
    deck.slides[0].claimIds = ["C1"];
    deck.slides[0].sourceUrls = ["https://example.com/source"];
    deck.slides[0].visualPlanData = { series: [{ label: "Market", value: 42, claim_ids: ["C1"] }] };
    deck.slides[0].visualReferences = [{
      url: "https://example.com/reference",
      description: "Market context",
      purpose: "Ground the visual",
      sourceType: "primary",
      license: "Reference only",
      claimIds: ["C1"],
    }];
    const prompt = buildMarkdownSlideDesignerPrompt("reports/plan.md", deck, "atlas");
    expect(prompt).toContain('"layout": "image-right"');
    expect(prompt).toContain('"image_required": true');
    expect(prompt).toContain("minimum_images=1");
    expect(prompt).toContain("estimated at USD 0.0336");
    expect(prompt).toContain("Slide Designer quality score: 100/100");
    expect(prompt).toContain("Render-time checks still required");
    expect(prompt).toContain('"image_prompt": "Editorial market scene');
    expect(prompt).toContain("Do not silently replace a selected layout");
    expect(prompt).toContain("13.333 × 7.5 inches (16:9)");
    expect(prompt).toContain('"visual_plan_data"');
    expect(prompt).toContain('"source_type": "primary"');
    expect(prompt).toContain('"claim_ids": [');
    expect(prompt).toContain("grouped visual-review batch");
    expect(prompt).toContain("contact sheet");
    expect(prompt).toContain("Match template");
    const playfulPrompt = buildMarkdownSlideDesignerPrompt("reports/plan.md", deck, "atlas", "playful");
    expect(playfulPrompt).toContain("copyrighted characters");
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
    const preview = screen.getByTestId("slide-preview");
    expect(preview.textContent).toContain("A better choice");
    expect(preview.getAttribute("data-aspect-ratio")).toBe("16:9");
    expect(preview.getAttribute("data-slide-width-inches")).toBe("13.333");
    expect(preview.getAttribute("data-slide-height-inches")).toBe("7.5");
    expect(preview.textContent).toContain("Widescreen 16:9 · 13.333 × 7.5 in");
    fireEvent.click(screen.getByRole("button", { name: "Continue to design" }));
    fireEvent.click(screen.getByRole("button", { name: /Two columns/i }));
    expect(screen.getByTestId("slide-preview").className).toContain("layout-two-column");
    fireEvent.click(screen.getByRole("button", { name: "Review deck" }));
    fireEvent.click(screen.getByRole("button", { name: "Create in composer" }));
    await waitFor(() => expect(onCreate).toHaveBeenCalledOnce());
    expect(screen.queryByRole("dialog")).toBeNull();
    expect(onCreate.mock.calls[0][0]).toContain('"layout": "two-column"');
  });

  it("automatically applies a matching Deep Research visual ledger", async () => {
    const visualArtifacts = [
      ...artifacts,
      {
        path: "reports/strategy.claims.json",
        name: "strategy.claims.json",
        kind: "code",
        size: 400,
        modified_at: 2,
      },
    ];
    vi.spyOn(api, "readArtifact").mockImplementation(async (_sessionId, artifactPath) => artifactPath.endsWith(".claims.json")
      ? {
        ok: true,
        path: artifactPath,
        kind: "code",
        content: JSON.stringify({
          schema_version: "openworker.deep-research.v2",
          sections: [{
            title: "The choice",
            takeaway: "The evidence favors option A.",
            claim_ids: ["C1"],
            representation: {
              type: "table",
              reason: "The alternatives need a direct comparison.",
              data: { columns: ["Option", "Score"], rows: [["A", "82"], ["B", "61"]] },
            },
            visual_references: [{
              url: "https://example.com/context.jpg",
              description: "Decision workshop with negative space",
              purpose: "Illustrate the decision context",
              license: "Reference only",
            }],
          }],
        }),
      }
      : {
        ok: true,
        path: artifactPath,
        kind: "markdown",
        content: "# Strategy\n## The choice\nOriginal narrative.",
      });

    render(<MarkdownSlideDesigner sessionId="session-1" artifacts={visualArtifacts} onCreate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Slide Designer/i }));
    await waitFor(() => expect(screen.getByText("Research visual plan applied to 1 section.")).toBeTruthy());
    expect(api.readArtifact).toHaveBeenCalledWith("session-1", "reports/strategy.claims.json");
    expect(screen.getByTestId("slide-preview").className).toContain("layout-table");
    expect(screen.getByTestId("slide-preview").textContent).toContain("Option");
    expect(screen.getByTestId("slide-preview").textContent).toContain("82");
    fireEvent.click(screen.getByRole("button", { name: "Continue to design" }));
    expect(screen.getByText("1 research visual reference")).toBeTruthy();
    expect(screen.getByText("Decision workshop with negative space")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Use as visual direction" }));
    expect(screen.getByTestId("slide-preview").className).toContain("layout-image-right");
    expect((screen.getByLabelText("Generate an original visual") as HTMLInputElement).checked).toBe(true);
  });

  it("explains blocked creation instead of leaving an inert composer button", async () => {
    vi.spyOn(api, "readArtifact").mockResolvedValue({
      ok: true,
      path: "reports/strategy.md",
      kind: "markdown",
      content: "# Strategy\n## Evidence\nOne message.",
    });
    render(<MarkdownSlideDesigner sessionId="session-1" artifacts={artifacts} onCreate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Slide Designer/i }));
    await waitFor(() => expect(screen.getByTestId("slide-preview")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Continue to design" }));
    fireEvent.click(screen.getByLabelText("Generate an original visual"));
    fireEvent.click(screen.getByRole("button", { name: "Review deck" }));
    const create = screen.getByRole("button", { name: "Start visual review" });
    expect((create as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(create);
    expect(screen.getByText("Resolve the required review items before creating the presentation.")).toBeTruthy();
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
      target: { value: "dashboard-pro" },
    });
    expect(preview.dataset.template).toBe("dashboard-pro");
    expect(preview.dataset.transition).toBe("push");
    expect(preview.dataset.motif).toBe("chart");
    expect(preview.getAttribute("style")).not.toBe(atlasStyle);
    expect(screen.getByText(/Dark analytical control room/i)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Presentation template"), {
      target: { value: "botanical-noir" },
    });
    expect(preview.dataset.composition).toBe("botanical");
    expect(screen.getByText(/Forest canopy/i)).toBeTruthy();
    expect(Number(preview.dataset.previewContrast)).toBeGreaterThanOrEqual(4.5);
    expect(screen.getByLabelText("Presentation template").querySelectorAll("option")).toHaveLength(14);
    expect(screen.getByLabelText("Presentation template").querySelectorAll("optgroup")).toHaveLength(6);
    expect(screen.queryByRole("option", { name: "Neon Flow" })).toBeNull();
    expect(screen.getByLabelText("Slide styles").querySelectorAll("button")).toHaveLength(36);
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
    fireEvent.click(screen.getByRole("button", { name: "Continue to design" }));
    expect(screen.getByText("Chart data")).toBeTruthy();
  });

  it("keeps storytelling in Content and structured visual editing in Design", async () => {
    vi.spyOn(api, "readArtifact").mockResolvedValue({
      ok: true,
      path: "reports/strategy.md",
      kind: "markdown",
      content: "# Strategy\n## Growth\nKeep the source content.\n- Enterprise | 64\n- Consumer | 36",
    });
    render(<MarkdownSlideDesigner sessionId="session-1" artifacts={artifacts} onCreate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Slide Designer/i }));
    await waitFor(() => expect(screen.getByTestId("slide-preview")).toBeTruthy());
    expect(screen.getByText("Story and content")).toBeTruthy();
    expect(screen.getByText("Story role")).toBeTruthy();
    expect(screen.queryByText("Change visual type")).toBeNull();
    expect(screen.queryByRole("button", { name: "Bar chart Compare values" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Continue to design" }));
    expect(screen.getAllByText("Standard").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByText("Change visual type"));
    fireEvent.click(screen.getByRole("button", { name: "Bar chart Compare values" }));
    expect(screen.getByTestId("slide-preview").className).toContain("layout-bar-chart");
    expect(screen.getByText("Chart data")).toBeTruthy();
    expect((screen.getByLabelText("Label 1") as HTMLInputElement).value).toBe("Enterprise");
    expect((screen.getByLabelText("Value 1") as HTMLInputElement).value).toBe("64");
    fireEvent.change(screen.getByLabelText("Value 1"), { target: { value: "72" } });
    expect(screen.getByTestId("slide-preview").textContent).toContain("72");
    fireEvent.click(screen.getByRole("button", { name: "+ Add data row" }));
    expect(screen.getByLabelText("Label 3")).toBeTruthy();
    fireEvent.click(screen.getByLabelText("Move row 2 up"));
    expect((screen.getByLabelText("Label 1") as HTMLInputElement).value).toBe("Consumer");
    fireEvent.click(screen.getByLabelText("Remove row 3"));
    expect(screen.queryByLabelText("Label 3")).toBeNull();
  });

  it("opens Markdown tables in a spreadsheet-like grid and accepts pasted cells", async () => {
    vi.spyOn(api, "readArtifact").mockResolvedValue({
      ok: true,
      path: "reports/options-storyboard.md",
      kind: "markdown",
      content: `# Options
## Comparison
\`\`\`openworker-visual
{"type":"table","data":{"columns":["Option","Cost"],"rows":[["A","10"],["B","20"]]}}
\`\`\``,
    });
    render(<MarkdownSlideDesigner sessionId="session-1" artifacts={artifacts} onCreate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Slide Designer/i }));
    await waitFor(() => expect(screen.getByTestId("slide-preview")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Continue to design" }));
    expect(screen.getByRole("grid", { name: "Table data grid" })).toBeTruthy();
    expect((screen.getByLabelText("Row 2 column 1") as HTMLInputElement).value).toBe("A");
    fireEvent.paste(screen.getByLabelText("Row 2 column 1"), {
      clipboardData: { getData: () => "Enterprise\t72\nConsumer\t28" },
    });
    expect((screen.getByLabelText("Row 2 column 1") as HTMLInputElement).value).toBe("Enterprise");
    expect((screen.getByLabelText("Row 3 column 2") as HTMLInputElement).value).toBe("28");
    fireEvent.click(screen.getByRole("button", { name: "+ Row" }));
    expect(screen.getByLabelText("Row 4 column 1")).toBeTruthy();
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
    expect(screen.getByRole("region", { name: "Visual review batch" })).toBeTruthy();
    expect(screen.getByText(/A calm editorial scene/)).toBeTruthy();
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

  it("scores content, evidence, structure, visuals, and pending render checks", () => {
    const deck = parseMarkdownDeck("# Deck\n## Evidence\nA sourced claim.\n- Segment A | 42");
    deck.slides[0].layout = "bar-chart";
    deck.slides[0].claimIds = ["C1"];
    deck.slides[0].imageRequired = true;
    const report = presentationQualityReport(deck, "atlas");
    expect(report.passed).toBe(false);
    expect(report.score).toBeLessThan(100);
    expect(report.metrics).toMatchObject({
      slides: 1,
      structuredSlides: 1,
      claims: 1,
      unsourcedClaims: 1,
      plannedImages: 1,
      readyImages: 0,
    });
    expect(report.findings).toEqual(expect.arrayContaining([
      expect.objectContaining({ category: "Data", severity: "critical", autoFixable: true }),
      expect.objectContaining({ category: "Evidence", severity: "critical", autoFixable: false }),
      expect.objectContaining({ category: "Visuals", severity: "critical", autoFixable: true }),
    ]));
    expect(report.renderChecks).toContain("Overlap, clipping, and off-canvas objects");
  });

  it("applies only safe automatic fixes without inventing evidence or chart data", () => {
    const deck = parseMarkdownDeck("# Deck\n## Placeholder\nA decision supported by one row.\n- Segment A | 42");
    deck.slides[0].title = "";
    deck.slides[0].layout = "bar-chart";
    deck.slides[0].imageRequired = true;
    deck.slides[0].claimIds = ["C1"];
    const fixed = autoFixPresentation(deck);
    expect(fixed.deck.slides[0].title).toContain("A decision supported");
    expect(fixed.deck.slides[0].layout).toBe("auto");
    expect(fixed.deck.slides[0].imagePrompt).toContain("Original editorial 16:9 visual");
    expect(fixed.deck.slides[0].sourceUrls).toEqual([]);
    expect(fixed.deck.slides[0].bullets).toEqual(["Segment A | 42"]);
    expect(fixed.fixes).toHaveLength(3);
    expect(presentationQualityReport(fixed.deck).findings).toEqual(expect.arrayContaining([
      expect.objectContaining({ category: "Evidence", autoFixable: false }),
    ]));
  });

  it("shows the quality score and fixes safe findings from the review step", async () => {
    vi.spyOn(api, "readArtifact").mockResolvedValue({
      ok: true,
      path: "reports/strategy.md",
      kind: "markdown",
      content: "# Strategy\n## Evidence\nOne message.",
    });
    render(<MarkdownSlideDesigner sessionId="session-1" artifacts={artifacts} onCreate={vi.fn()} />);
    fireEvent.click(screen.getByRole("button", { name: /Slide Designer/i }));
    await waitFor(() => expect(screen.getByTestId("slide-preview")).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "Continue to design" }));
    fireEvent.click(screen.getByRole("button", { name: "Bar chart Compare values" }));
    fireEvent.click(screen.getByLabelText("Generate an original visual"));
    fireEvent.click(screen.getByRole("button", { name: "Review deck" }));
    expect(screen.getByRole("region", { name: "Presentation quality check" })).toBeTruthy();
    expect(screen.getByText("Presentation Quality Check")).toBeTruthy();
    expect(screen.getByText("0/1")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Fix automatically" }));
    expect(screen.getByText(/safe fixes applied/i)).toBeTruthy();
    expect(screen.getByText("All editable-content checks passed.")).toBeTruthy();
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
