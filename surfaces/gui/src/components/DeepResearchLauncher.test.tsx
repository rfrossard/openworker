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
});
