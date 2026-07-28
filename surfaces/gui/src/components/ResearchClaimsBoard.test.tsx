import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ResearchRun } from "../api";
import { ResearchClaimsBoard } from "./ResearchClaimsBoard";

const run = {
  run_id: "research-grounded",
  session_id: "session-a",
  question: "Ground this",
  depth: "standard",
  method: "grounded_claims",
  plan: ["Verify"],
  status: "completed",
  source_limit: 10,
  agent_limit: 1,
  sources_found: 2,
  artifact_paths_at_start: [],
  browser_history_count_at_start: 0,
  browser_evidence_count_at_start: 0,
  artifact_paths: [],
  artifact_count: 2,
  browser_navigation_count: 2,
  browser_evidence_count: 2,
  evidence: [],
  claims: [
    {
      claim_id: "C1",
      claim: "The primary source supports the measured result.",
      status: "supported",
      confidence: 0.9,
      sources: ["https://example.com/study"],
      justification: "Directly reported.",
      counterevidence: "",
    },
    {
      claim_id: "C2",
      claim: "The broader interpretation remains disputed.",
      status: "conflicting",
      confidence: 0.55,
      sources: ["https://example.com/review"],
      justification: "Sources disagree.",
      counterevidence: "A later review reaches a different conclusion.",
    },
  ],
  created_at: "2026-07-27T00:00:00Z",
  updated_at: "2026-07-27T00:00:00Z",
} satisfies ResearchRun;

describe("ResearchClaimsBoard", () => {
  it("shows claim coverage, confidence, and counterevidence", () => {
    render(<ResearchClaimsBoard run={run} />);

    expect(screen.getByText("Claim Ledger (2)")).toBeTruthy();
    expect(screen.getByText("50% fully supported")).toBeTruthy();
    expect(screen.getByText("90% confidence")).toBeTruthy();
    expect(screen.getByText(/A later review reaches/)).toBeTruthy();
  });
});
