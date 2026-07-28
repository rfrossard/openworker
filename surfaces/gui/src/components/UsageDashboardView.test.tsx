import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AccountCard, formatAccountUpdatedAt, OperationUsage } from "./UsageDashboardView";

describe("provider balance update time", () => {
  it("renders the provider-specific timestamp below an official balance", () => {
    const updatedAt = "2026-07-28T05:52:52.629963+00:00";
    render(
      <AccountCard
        name="DeepSeek"
        account={{
          configured: true,
          status: "available",
          available: true,
          balances: [
            { currency: "USD", total: 34.74, granted: 0, topped_up: 34.74 },
          ],
          scope: "account",
          source: "official",
          updated_at: updatedAt,
        }}
      />,
    );

    expect(screen.getByText("USD 34.74")).toBeTruthy();
    expect(screen.getByText(/Last updated/).getAttribute("title")).toBe(updatedAt);
  });

  it("does not invent a time when the provider omitted it", () => {
    expect(formatAccountUpdatedAt()).toBe("Update time unavailable");
    expect(formatAccountUpdatedAt("invalid")).toBe("Update time unavailable");
  });

  it("renders dynamic locally recorded Gemini image usage separately", () => {
    render(
      <AccountCard
        name="Google · Gemini Nano Banana 2 Lite"
        account={{
          configured: true,
          status: "local_estimate",
          balances: [],
          local_spend: 0.0672,
          units: 2,
          unit_kind: "image",
          model: "Gemini Nano Banana 2 Lite",
          model_id: "gemini-3.1-flash-lite-image",
          scope: "local_sessions",
          source: "estimated",
          message: "Locally recorded estimate.",
          updated_at: "2026-07-28T10:00:00+00:00",
        }}
      />,
    );

    expect(screen.getByText("USD 0.0672")).toBeTruthy();
    expect(screen.getByText(/2 images · locally recorded estimate/)).toBeTruthy();
    expect(screen.getByText(/local estimate/)).toBeTruthy();
  });
});

describe("generated media usage", () => {
  it("shows Gemini image count and estimated cost explicitly", () => {
    render(
      <OperationUsage
        operations={{
          "Gemini Nano Banana 2 Lite": {
            type: "image",
            provider: "Google",
            model_id: "gemini-3.1-flash-lite-image",
            units: 2,
            cost: 0.0672,
            measurement: "estimated",
          },
        }}
      />,
    );

    expect(screen.getByText("Gemini Nano Banana 2 Lite")).toBeTruthy();
    expect(screen.getByText("$0.0672")).toBeTruthy();
    expect(screen.getByText("2")).toBeTruthy();
  });

  it("explains why Gemini has no row before a successful generation", () => {
    render(<OperationUsage operations={{}} />);
    expect(screen.getByText(/No billed image or audio generations/)).toBeTruthy();
  });
});
