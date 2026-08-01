import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

  it("builds an atomic, contradiction-aware grounded claims task", () => {
    const prompt = buildDeepResearchPrompt({
      question: "Which intervention has the strongest evidence?",
      depth: "standard",
      plan: "Decompose the question\nVerify each claim",
      method: "grounded_claims",
    });

    expect(prompt).toContain("independently verifiable atomic claims");
    expect(prompt).toContain("plausible counterevidence");
    expect(prompt).toContain("Unsupported claims must not appear as facts");
    expect(prompt).toContain(".claims.json");
    expect(prompt).toContain("final entailment check");
    expect(prompt).toContain('"schema_version": "openworker.deep-research.v2"');
    expect(prompt).toContain('"sections"');
    expect(prompt).toContain("table | bar_chart | donut_chart | radar_chart | sankey_diagram | word_cloud");
    expect(prompt).toContain("layout_recommendation");
    expect(prompt).toContain("Every numeric chart/table value, exact quote, relationship, event, and process step");
    expect(prompt).toContain("visual_references");
    expect(prompt).toContain("Never invent content to complete");
    expect(prompt.match(/"schema_version": "openworker\.deep-research\.v2"/g)).toHaveLength(1);
  });

  it("builds a researched, image-aware, QA-gated presentation task", () => {
    const prompt = buildDeepResearchPrompt({
      question: "How should we launch the new product?",
      depth: "deep",
      plan: "Research the market\nBuild the recommendation",
      method: "grounded_claims",
      deliverable: "presentation",
      audience: "Executive leadership",
      slideCount: 12,
      visualDirection: "Editorial with bold photography",
      imageMode: "generate",
      imageQuality: "high",
    });

    expect(prompt).toContain("Target 12 slides");
    expect(prompt).toContain("Executive leadership");
    expect(prompt).toContain("two-stage workflow inspired by PPTAgent");
    expect(prompt).toContain("presentation-studio skill");
    expect(prompt).toContain("native build_presentation tool");
    expect(prompt).toContain("Never create the PDF with a Markdown writer");
    expect(prompt).toContain("Presenton-style local/BYOK");
    expect(prompt).toContain("Gemini Nano Banana 2 Lite");
    expect(prompt).toContain("reports/assets/");
    expect(prompt).toContain("both reports/<descriptive-name>.pptx and reports/<descriptive-name>.pdf");
    expect(prompt).toContain("speaker notes");
    expect(prompt).toContain("inspect for overlap");
    expect(prompt).toContain('template_id="atlas"');
    expect(prompt).toContain("minimum_images=5");
    expect(prompt).toContain("visual_plan_complete=true");
    expect(prompt).toContain("result.path exactly");
    expect(prompt).toContain("add sections for Slide Designer");
    expect(prompt).toContain("Every numeric chart/table value");
    expect(prompt).toContain("```openworker-visual");
    expect(prompt).toContain('"type": "table"');
    expect(prompt).toContain("For big_number, provide data.value");
    expect(prompt).toContain("data.period, data.baseline, and data.source_claim_ids");
    expect(prompt).toContain("storyboard blocks and the companion .claims.json visual ledger must agree");
    expect(prompt).toContain('"visual_question"');
    expect(prompt).toContain('"rejected_representations"');
    expect(prompt).toContain("Never turn ordinary bullets into a table");
    expect(prompt).toContain("Use a flowchart only when there is a decision, branch, loop, exception, or alternative path");
    expect(prompt).toContain("understandable within five seconds");
  });

  it("persists the run before letting the user review it", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      json: async () => ({
        ok: true,
        run: {
          run_id: "research-test123",
          session_id: "session-a",
          question: "Compare secure browser frameworks",
          depth: "deep",
          plan: ["Compare evidence"],
          status: "planned",
          source_limit: 20,
          agent_limit: 1,
          sources_found: 0,
          created_at: "2026-07-27T00:00:00Z",
          updated_at: "2026-07-27T00:00:00Z",
        },
      }),
    } as Response);
    const onCreate = vi.fn();
    render(<DeepResearchLauncher sessionId="session-a" onCreate={onCreate} />);

    fireEvent.click(screen.getAllByRole("button", { name: "Deep Research" }).slice(-1)[0]);
    fireEvent.change(screen.getByLabelText("Research question"), {
      target: { value: "Compare secure browser frameworks" },
    });
    fireEvent.click(screen.getByRole("button", { name: /^Deep at least 20 credible sources$/ }));
    fireEvent.click(screen.getByRole("button", { name: "Continue in composer" }));

    await waitFor(() => expect(onCreate).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/v1/sessions/session-a/research-runs"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(onCreate.mock.calls[0][0]).toContain("Compare secure browser frameworks");
    expect(onCreate.mock.calls[0][0]).toContain("at least 20 credible sources");
    expect(onCreate.mock.calls[0][0]).toContain("research-test123");
    const request = JSON.parse(
      (fetchMock.mock.calls[0][1] as RequestInit).body as string,
    );
    expect(request.method).toBe("grounded_claims");
    expect(request.deliverable).toBe("report");
    expect(request.image_mode).toBe("generate");
    expect(request.image_quality).toBe("medium");
    expect(request.plan_steps).toHaveLength(4);
    fetchMock.mockRestore();
  });

  it("reopens and edits a planned research project", async () => {
    const run = {
      run_id: "research-existing",
      session_id: "session-a",
      question: "Original question",
      depth: "quick" as const,
      plan: ["Original step"],
      status: "planned" as const,
      source_limit: 5,
      agent_limit: 1,
      sources_found: 0,
      artifact_paths_at_start: [],
      browser_history_count_at_start: 0,
      browser_evidence_count_at_start: 0,
      artifact_paths: [],
      artifact_count: 0,
      browser_navigation_count: 0,
      browser_evidence_count: 0,
      evidence: [],
      created_at: "2026-07-27T00:00:00Z",
      updated_at: "2026-07-27T00:00:00Z",
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      json: async () => ({
        ok: true,
        run: { ...run, question: "Updated question", plan: ["Updated step"] },
      }),
    } as Response);
    const onCreate = vi.fn();
    render(
      <DeepResearchLauncher
        sessionId="session-a"
        editingRun={run}
        onCreate={onCreate}
      />,
    );

    expect(screen.getByRole("heading", { name: "Edit Deep Research" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Research question"), {
      target: { value: "Updated question" },
    });
    fireEvent.change(screen.getByLabelText("Research plan step 1"), {
      target: { value: "Updated step" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save to composer" }));

    await waitFor(() => expect(onCreate).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/research-runs/research-existing"),
      expect.objectContaining({ method: "PATCH" }),
    );
    expect(onCreate.mock.calls[0][0]).toContain("Updated question");
    expect(onCreate.mock.calls[0][0]).toContain("Updated step");
    fetchMock.mockRestore();
  });

  it("lets the user select, reorder, and edit the executable research steps", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      json: async () => ({ ok: true, run: { run_id: "research-plan", session_id: "session-a" } }),
    } as Response);
    const onCreate = vi.fn();
    render(<DeepResearchLauncher sessionId="session-a" onCreate={onCreate} />);

    fireEvent.click(screen.getAllByRole("button", { name: "Deep Research" }).slice(-1)[0]);
    fireEvent.change(screen.getByLabelText("Research question"), { target: { value: "Plan test" } });
    fireEvent.click(screen.getByLabelText("Include step 2"));
    fireEvent.click(screen.getByLabelText("Move step 4 up"));
    fireEvent.change(screen.getByLabelText("Research plan step 3"), { target: { value: "Finish with a decision" } });
    fireEvent.click(screen.getByRole("button", { name: "Continue in composer" }));

    await waitFor(() => expect(onCreate).toHaveBeenCalledTimes(1));
    const request = JSON.parse((fetchMock.mock.calls[0][1] as RequestInit).body as string);
    expect(request.plan).not.toContain("Find primary sources and strong independent coverage");
    expect(request.plan_steps[2].text).toBe("Finish with a decision");
    expect(request.plan_steps.some((step: { enabled: boolean }) => !step.enabled)).toBe(true);
    fetchMock.mockRestore();
  });

  it("previews bounded Wide Research lanes without implying parallel execution", () => {
    render(<DeepResearchLauncher sessionId="session-a" onCreate={vi.fn()} />);
    const launchers = screen.getAllByRole("button", { name: "Deep Research" });
    fireEvent.click(launchers[launchers.length - 1]);
    const lanes = screen.getByRole("region", { name: "Wide Research lanes" });
    expect(lanes.textContent).toContain("4 lanes");
    expect(lanes.textContent).toContain("Execution remains single-agent");
    expect(lanes.textContent).toContain("3 sources");
  });
});
