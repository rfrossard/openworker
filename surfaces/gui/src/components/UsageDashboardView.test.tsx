import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AccountCard, formatAccountUpdatedAt } from "./UsageDashboardView";

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
});
