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

    fireEvent.click(screen.getByRole("button", { name: "New research" }));
    fireEvent.change(screen.getByLabelText("Research question"), {
      target: { value: "Compare secure browser frameworks" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Deep/ }));
    fireEvent.click(screen.getByRole("button", { name: "Review in composer" }));

    await waitFor(() => expect(onCreate).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/v1/sessions/session-a/research-runs"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(onCreate.mock.calls[0][0]).toContain("Compare secure browser frameworks");
    expect(onCreate.mock.calls[0][0]).toContain("at least 20 credible sources");
    expect(onCreate.mock.calls[0][0]).toContain("research-test123");
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

    expect(screen.getByRole("heading", { name: "Edit Research Project" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Research question"), {
      target: { value: "Updated question" },
    });
    fireEvent.change(screen.getByLabelText("Research plan"), {
      target: { value: "Updated step" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save and review" }));

    await waitFor(() => expect(onCreate).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/research-runs/research-existing"),
      expect.objectContaining({ method: "PATCH" }),
    );
    expect(onCreate.mock.calls[0][0]).toContain("Updated question");
    expect(onCreate.mock.calls[0][0]).toContain("Updated step");
    fetchMock.mockRestore();
  });
});
