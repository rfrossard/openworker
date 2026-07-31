import { expect } from "@playwright/test";
import { test } from "./fixtures";

const OPEN_BROWSER = {
  open: true,
  url: "https://www.selenium.dev/selenium/web/web-form.html",
  title: "Web form",
  status: "open",
  last_action: "select",
  last_result: "ok",
  last_error: "",
  screenshot_data_url: "",
  updated_at: "2026-07-31T02:00:00Z",
  controls: [],
  always_allow_reads: true,
  allowed_domains: [],
  history: [],
  evidence: [],
  media: [],
  streaming_media: [],
  streaming_media_status: "idle",
  streaming_media_error: "",
  streaming_media_progress: {},
  pending_action: {},
};

test("an active Secure Browser remains recoverable after the side panel is hidden", async ({
  page,
}) => {
  await page.route("**/v1/browser/state?**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(OPEN_BROWSER),
    }),
  );
  await page.goto("/");

  await expect(page.getByText("Isolated session active")).toBeVisible();
  await page.getByRole("button", { name: "Hide side panel" }).click();

  const browserButton = page.getByRole("button", { name: "Browser", exact: true });
  await expect(browserButton).toBeVisible();
  await expect(browserButton).toHaveAttribute("title", "Show the active Secure Browser");

  await browserButton.click();
  await expect(page.getByText("Isolated session active")).toBeVisible();
  await expect(page.getByText("Web form", { exact: true })).toBeVisible();
});
