import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { BrowserActionInspector } from "./RightRail";

afterEach(cleanup);

describe("BrowserActionInspector", () => {
  it("explains the proposed target, risk, and expected outcome", () => {
    render(
      <BrowserActionInspector
        action={{
          tool_name: "browser_click",
          action: "Click",
          target: "#save",
          label: "Save draft",
          domain: "example.com",
          risk: "Page interaction",
          expected_result: "The selected page element is activated.",
          status: "pending",
        }}
      />,
    );

    expect(screen.getByText("Approval required")).toBeTruthy();
    expect(screen.getByText("Save draft")).toBeTruthy();
    expect(screen.getByText("example.com")).toBeTruthy();
    expect(screen.getByText("Page interaction")).toBeTruthy();
    expect(screen.getByText("The selected page element is activated.")).toBeTruthy();
    expect(screen.getByText("Approve or deny this action in the composer.")).toBeTruthy();
  });

  it("surfaces a stale target as a safe stop", () => {
    render(
      <BrowserActionInspector
        action={{
          tool_name: "browser_click",
          action: "Click",
          label: "Delete account",
          status: "stale",
          error: "The page changed before the action ran.",
        }}
      />,
    );

    expect(screen.getByText("Target changed")).toBeTruthy();
    expect(screen.getByText("The page changed before the action ran.")).toBeTruthy();
    expect(screen.queryByText("Approve or deny this action in the composer.")).toBeNull();
  });
});
