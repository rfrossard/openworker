import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { ResearchRun } from "../api";
import { ResearchEvidenceBoard } from "./ResearchEvidenceBoard";

const run: ResearchRun = {
  run_id: "research-test",
  session_id: "session-a",
  question: "Compare evidence",
  depth: "quick",
  plan: ["Collect"],
  status: "researching",
  source_limit: 5,
  agent_limit: 1,
  sources_found: 1,
  artifact_paths_at_start: [],
  browser_history_count_at_start: 0,
  browser_evidence_count_at_start: 0,
  artifact_paths: [],
  artifact_count: 0,
  browser_navigation_count: 1,
  browser_evidence_count: 1,
  evidence: [{
    evidence_id: "evidence-1",
    fingerprint: "fingerprint",
    url: "https://example.com/report",
    title: "Primary report",
    action: "open_url",
    captured_at: "2026-07-27T00:00:00Z",
    screenshot_sha256: "snapshot",
    status: "collected",
    note: "",
  }],
  created_at: "2026-07-27T00:00:00Z",
  updated_at: "2026-07-27T00:00:00Z",
};

describe("Research Evidence Board", () => {
  it("shows captured sources and updates their review status", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      json: async () => ({
        ok: true,
        evidence: { ...run.evidence[0], status: "verified" },
      }),
    } as Response);
    const onEvidenceUpdated = vi.fn();
    render(
      <ResearchEvidenceBoard
        sessionId="session-a"
        run={run}
        onEvidenceUpdated={onEvidenceUpdated}
      />,
    );

    fireEvent.click(screen.getByText("Evidence (1)"));
    expect(screen.getByText("Primary report")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Evidence status for Primary report"), {
      target: { value: "verified" },
    });

    await waitFor(() => expect(onEvidenceUpdated).toHaveBeenCalledTimes(1));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/evidence/evidence-1"),
      expect.objectContaining({ method: "PATCH" }),
    );
    fetchMock.mockRestore();
  });
});
