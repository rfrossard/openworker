import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

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
    expect(screen.getByText("This action can also be resolved from the composer.")).toBeTruthy();
  });

  it("resolves the same pending action directly beside the preview", () => {
    const decide = vi.fn();
    render(
      <BrowserActionInspector
        action={{
          tool_call_id: "call-browser-1",
          tool_name: "browser_click",
          action: "Click",
          label: "Save draft",
          status: "pending",
        }}
        canResolve
        onDecision={decide}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Approve once" }));
    expect(decide).toHaveBeenCalledTimes(1);
    expect(decide).toHaveBeenCalledWith("once");

    fireEvent.click(screen.getByRole("button", { name: "Deny" }));
    expect(decide).toHaveBeenCalledTimes(2);
    expect(decide).toHaveBeenLastCalledWith("deny");
  });

  it("disables both decisions after one has been sent", () => {
    render(
      <BrowserActionInspector
        action={{
          tool_call_id: "call-browser-2",
          tool_name: "browser_click",
          action: "Click",
          label: "Continue",
          status: "pending",
        }}
        canResolve
        resolving
        onDecision={vi.fn()}
      />,
    );

    expect((screen.getByRole("button", { name: "Approve once" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Deny" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole("status").textContent).toContain("Decision sent");
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
    expect(screen.queryByText("This action can also be resolved from the composer.")).toBeNull();
  });

  it("explains typing without rendering the proposed value", () => {
    const secret = "do-not-render-this-token";
    const { container } = render(
      <BrowserActionInspector
        action={{
          tool_name: "browser_type",
          action: "Type",
          label: "API token",
          domain: "example.com",
          risk: "Sensitive input",
          expected_result: "The field is replaced with the approved content.",
          content_summary: "Content hidden for privacy.",
          sensitive: true,
          status: "pending",
        }}
      />,
    );

    expect(screen.getByText("Content hidden for privacy.")).toBeTruthy();
    expect(screen.getByText("Sensitive input")).toBeTruthy();
    expect(container.textContent).not.toContain(secret);
  });

  it("shows the exact human-readable dropdown option", () => {
    render(
      <BrowserActionInspector
        action={{
          tool_name: "browser_select",
          action: "Select",
          label: "Country",
          domain: "example.com",
          risk: "Form selection",
          expected_result: "The dropdown changes to “Brazil”.",
          content_summary: "Selected option: Brazil",
          status: "pending",
        }}
      />,
    );

    expect(screen.getByText("Selected option: Brazil")).toBeTruthy();
    expect(screen.getByText("The dropdown changes to “Brazil”.")).toBeTruthy();
    expect(screen.getByText("Form selection")).toBeTruthy();
  });

  it("shows the file name and disclosure risk before upload", () => {
    const { container } = render(
      <BrowserActionInspector
        action={{
          tool_name: "browser_upload_file",
          action: "Upload",
          label: "Attach supporting document",
          domain: "example.com",
          risk: "File disclosure",
          expected_result: "“quarterly-report.pdf” is attached to this field.",
          content_summary: "File: quarterly-report.pdf",
          status: "pending",
        }}
      />,
    );

    expect(screen.getByText("Upload")).toBeTruthy();
    expect(screen.getByText("Attach supporting document")).toBeTruthy();
    expect(screen.getByText("File: quarterly-report.pdf")).toBeTruthy();
    expect(screen.getByText("File disclosure")).toBeTruthy();
    expect(container.textContent).not.toContain("/Users/");
  });
});
